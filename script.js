// Simple To-Do App with localStorage
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
const STORAGE_KEY = "todo.items.v1";

let state = { items: load(), filter: "all", q: "" };

const listEl = $("#list");
const tmpl = $("#item-template");
const form = $("#new-task-form");
const input = $("#task-input");
const priority = $("#priority");
const due = $("#due");
const search = $("#search");
const clearBtn = $("#clear-completed");
const countEl = $("#count");

// Init
bindUI();
render();

function load() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || []; }
  catch { return []; }
}
function save() { localStorage.setItem(STORAGE_KEY, JSON.stringify(state.items)); }

function bindUI() {
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    addItem(input.value.trim(), priority.value, due.value || null);
    form.reset();
    input.focus();
  });
  search.addEventListener("input", (e) => { state.q = e.target.value.toLowerCase(); render(); });
  $$('input[name="filter"]').forEach(r => r.addEventListener("change", (e) => { state.filter = e.target.value; render(); }));
  clearBtn.addEventListener("click", () => {
    state.items = state.items.filter(i => !i.completed);
    save(); render();
  });
}

function addItem(title, pri = "normal", dueISO = null) {
  if (!title) return;
  state.items.unshift({
    id: crypto.randomUUID(),
    title, priority: pri, due: dueISO,
    completed: false, createdAt: Date.now()
  });
  save(); render();
}
function setCompleted(id, val) {
  const it = state.items.find(i => i.id === id); if (!it) return;
  it.completed = !!val; save(); render();
}
function updateItem(id, fields) {
  const it = state.items.find(i => i.id === id); if (!it) return;
  Object.assign(it, fields); save(); render();
}
function removeItem(id) {
  state.items = state.items.filter(i => i.id !== id); save(); render();
}

function applyFilters(items) {
  const byFilter = items.filter(i => state.filter === "active" ? !i.completed : state.filter === "completed" ? i.completed : true);
  const byQuery = state.q ? byFilter.filter(i => i.title.toLowerCase().includes(state.q)) : byFilter;
  const priRank = { high: 0, normal: 1, low: 2 };
  return byQuery.sort((a, b) => {
    const p = priRank[a.priority] - priRank[b.priority];
    if (p) return p;
    if (a.due && b.due) return a.due.localeCompare(b.due);
    if (a.due) return -1;
    if (b.due) return 1;
    return b.createdAt - a.createdAt;
  });
}

function render() {
  listEl.innerHTML = "";
  const items = applyFilters(state.items);
  items.forEach(item => listEl.appendChild(renderItem(item)));
  const remaining = state.items.filter(i => !i.completed).length;
  countEl.textContent = `${remaining} item${remaining === 1 ? "" : "s"} left`;
}

function renderItem(item) {
  const node = tmpl.content.firstElementChild.cloneNode(true);
  const li = node;
  const chk = node.querySelector(".toggle");
  const title = node.querySelector(".title");
  const priBadge = node.querySelector(".badge.priority");
  const dueBadge = node.querySelector(".badge.due");
  const btnEdit = node.querySelector(".edit");
  const btnSave = node.querySelector(".save");
  const btnCancel = node.querySelector(".cancel");
  const btnDelete = node.querySelector(".delete");

  li.dataset.id = item.id;
  if (item.completed) li.classList.add("completed");

  chk.checked = item.completed;
  chk.addEventListener("change", () => setCompleted(item.id, chk.checked));

  title.value = item.title;
  title.readOnly = true;

  priBadge.textContent = item.priority;
  priBadge.dataset.p = item.priority;

  if (item.due) {
    dueBadge.textContent = `Due ${formatDate(item.due)}`;
    dueBadge.hidden = false;
    dueBadge.dataset.overdue = String(isOverdue(item.due) && !item.completed);
  } else {
    dueBadge.hidden = true;
  }

  btnEdit.addEventListener("click", () => enterEdit());
  btnSave.addEventListener("click", () => commitEdit());
  btnCancel.addEventListener("click", () => exitEdit(true));
  btnDelete.addEventListener("click", () => removeItem(item.id));

  function enterEdit() {
    title.readOnly = false;
    title.focus();
    title.selectionStart = title.value.length;
    toggleEditButtons(true);
  }
  function exitEdit(cancel = false) {
    title.readOnly = true;
    if (cancel) title.value = item.title;
    toggleEditButtons(false);
  }
  function commitEdit() {
    const newTitle = title.value.trim();
    if (!newTitle) { title.value = item.title; exitEdit(); return; }
    updateItem(item.id, { title: newTitle });
  }
  function toggleEditButtons(isEditing) {
    btnEdit.hidden = isEditing;
    btnSave.hidden = !isEditing;
    btnCancel.hidden = !isEditing;
  }

  return node;
}

function isOverdue(iso) {
  const today = new Date(); today.setHours(0,0,0,0);
  const d = new Date(iso + "T00:00:00");
  return d < today;
}
function formatDate(iso) {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString(undefined, { year:"numeric", month:"short", day:"numeric" });
}

// Seed for first-time use
if (state.items.length === 0) {
  addItem("Welcome. Edit me or check me off.");
  addItem("Star important tasks with High priority.", "high");
  addItem("Try filters and search.", "low");
}
