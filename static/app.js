// API базовый URL
const API_BASE = '/api';

// Состояние приложения
let currentUser = null;
let authToken = null;

// Всегда получать актуальный токен (localStorage — источник правды)
function getAuthHeaders() {
    const token = (authToken || localStorage.getItem('authToken') || '').trim();
    if (!token) return null;
    return { 'Authorization': `Bearer ${token}` };
}

// Инициализация
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    setupEventListeners();
});

// Проверка аутентификации
function checkAuth() {
    const token = (localStorage.getItem('authToken') || '').trim();
    if (token) {
        authToken = token;
        loadUserInfo();
    } else {
        showLogin();
    }
}

// Загрузка информации о пользователе
async function loadUserInfo() {
    const tokenAtStart = authToken;
    const headers = getAuthHeaders();
    if (!headers) {
        showLogin();
        return;
    }
    try {
        const response = await fetch(`${API_BASE}/users/me`, { headers });
        
        if (response.ok) {
            currentUser = await response.json();
            showApp();
        } else {
            // Не очищаем токен, если он изменился (успешный логин пока мы ждали)
            if (authToken === tokenAtStart) {
                localStorage.removeItem('authToken');
                authToken = null;
                showLogin();
            }
        }
    } catch (error) {
        console.error('Ошибка загрузки пользователя:', error);
        if (authToken === tokenAtStart) {
            localStorage.removeItem('authToken');
            authToken = null;
            showLogin();
        }
    }
}

// Показать форму входа
function showLogin() {
    document.getElementById('login-section').style.display = 'flex';
    document.getElementById('app-section').style.display = 'none';
    document.getElementById('logout-btn').style.display = 'none';
}

// Показать приложение
function showApp() {
    document.getElementById('login-section').style.display = 'none';
    document.getElementById('app-section').style.display = 'block';
    document.getElementById('logout-btn').style.display = 'block';
    const tgBtn = document.getElementById('test-tg-btn');
    if (tgBtn) {
        tgBtn.style.display = currentUser.telegram_id ? 'inline-block' : 'none';
    }
    document.getElementById('user-info').textContent = currentUser.full_name || currentUser.username || currentUser.login;
    loadData();
}

// Настройка обработчиков событий
function setupEventListeners() {
    // Форма входа
    document.getElementById('login-form').addEventListener('submit', handleLogin);
    
    // Выход
    document.getElementById('logout-btn').addEventListener('click', handleLogout);
    // Тест Telegram
    document.getElementById('test-tg-btn')?.addEventListener('click', testTelegram);
    
    // Табы
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });
    
    // Кнопки создания
    document.getElementById('create-task-btn')?.addEventListener('click', () => showCreateTaskModal());
    document.getElementById('create-workgroup-btn')?.addEventListener('click', () => showCreateWorkgroupModal());
    document.getElementById('create-user-btn')?.addEventListener('click', () => showCreateUserModal());
    document.getElementById('add-note-btn')?.addEventListener('click', () => addStickyNote());
}

// Вход
async function handleLogin(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    const loginData = {
        login: formData.get('login'),
        password: formData.get('password')
    };
    
    try {
        const response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(loginData)
        });
        
        if (response.ok) {
            const data = await response.json();
            const token = (data.access_token || '').trim();
            if (!token) {
                alert('Ошибка: сервер не вернул токен');
                return;
            }
            authToken = token;
            localStorage.setItem('authToken', authToken);
            currentUser = data.user;
            showApp();
        } else {
            const error = await response.json();
            alert('Ошибка входа: ' + (error.detail || 'Неверный логин или пароль'));
        }
    } catch (error) {
        console.error('Ошибка входа:', error);
        alert('Ошибка подключения к серверу');
    }
}

// Тест отправки в Telegram
async function testTelegram() {
    const headers = getAuthHeaders();
    if (!headers) { showLogin(); return; }
    try {
        const res = await fetch(`${API_BASE}/users/me/test-telegram`, { method: 'POST', headers });
        const data = await res.json().catch(() => ({}));
        if (res.ok) {
            alert('Сообщение отправлено! Проверьте Telegram.');
        } else {
            alert('Ошибка: ' + (data.detail || res.statusText));
        }
    } catch (e) {
        alert('Ошибка: ' + e.message);
    }
}

// Выход
function handleLogout() {
    localStorage.removeItem('authToken');
    authToken = null;
    currentUser = null;
    showLogin();
}

// Переключение табов
function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === `tab-${tabName}`);
    });
    loadData();
}

// Загрузка данных
function loadData() {
    const activeTab = document.querySelector('.tab-btn.active')?.dataset.tab;
    if (activeTab === 'tasks') {
        loadTasks();
    } else if (activeTab === 'timeline') {
        loadTimeline();
    } else if (activeTab === 'workgroups') {
        loadWorkgroups();
    } else if (activeTab === 'users') {
        loadUsers();
    } else if (activeTab === 'notes') {
        renderStickyNotes();
    }
}

// Загрузка задач
async function loadTasks() {
    const headers = getAuthHeaders();
    if (!headers) { showLogin(); return; }
    try {
        const response = await fetch(`${API_BASE}/tasks/`, { headers });
        
        if (response.ok) {
            const tasks = await response.json();
            renderTasks(tasks);
        } else if (response.status === 401) {
            localStorage.removeItem('authToken');
            authToken = null;
            showLogin();
        }
    } catch (error) {
        console.error('Ошибка загрузки задач:', error);
    }
}

// Отображение задач
function renderTasks(tasks) {
    const container = document.getElementById('tasks-list');
    container.innerHTML = tasks.map((task, i) => {
        const assignees = (task.assignees || []).map(a => a.full_name || a.username || a.login || 'ID ' + a.id).join(', ');
        const dueStr = task.due_date ? formatDate(task.due_date) : '';
        const pollStr = (task.poll_interval_days && task.poll_time) ? `Опрос: каждые ${task.poll_interval_days} дн. в ${task.poll_time}` : '';
        return `
        <div class="card" style="animation-delay: ${i * 50}ms">
            <div class="card-header">
                <div>
                    <div class="card-title">${task.title}</div>
                    <div class="card-description">${task.description || 'Без описания'}</div>
                </div>
            </div>
            <div class="card-meta">
                <span class="badge badge-${getStatusColor(task.status)}">${getStatusText(task.status)}</span>
                ${assignees ? `<span class="badge badge-primary" title="Исполнители">Исп.: ${assignees}</span>` : ''}
                ${dueStr ? `<span class="badge badge-warning" title="Срок">ДДЛ: ${dueStr}</span>` : ''}
                ${pollStr ? `<span class="badge badge-primary" title="Опрос">${pollStr}</span>` : ''}
            </div>
            <div class="card-actions">
                <button class="btn btn-sm btn-secondary" onclick="event.stopPropagation(); nudgeTask(${task.id})" title="Напомнить исполнителям в Telegram">Тыкнуть</button>
                <button class="btn btn-sm btn-primary" onclick="editTask(${task.id})">Редактировать</button>
                <button class="btn btn-sm btn-danger" onclick="deleteTask(${task.id})">Удалить</button>
            </div>
        </div>
    `}).join('');
}

// Таймлайн задач: линия 60% «В работе» / 40% «На проверке»; точки по ответам на тыки
let lastTimelineData = { tasks: [], workgroups: [] };
const TIMELINE_ZONES = [
    { pct: 60, label: 'В работе' },
    { pct: 40, label: 'На проверке' }
];

/** Позиция точки по индексу ответа и общему числу ответов (%). Если задача выполнена (Готово) — последняя точка в конце (100%). */
function getDotPositionPercent(responseIndex, totalCount, isDone) {
    if (isDone && totalCount > 0 && responseIndex === totalCount - 1) return 100;
    if (isDone && totalCount === 0) return 100;
    if (totalCount === 1) return 30;
    if (totalCount === 2) return responseIndex === 0 ? 30 : 80;
    if (totalCount >= 3) {
        if (responseIndex === 0) return 20;
        if (responseIndex === 1) return 40;
        return isDone ? 100 : 80;
    }
    return 30;
}

async function loadTimeline() {
    const headers = getAuthHeaders();
    if (!headers) { showLogin(); return; }
    try {
        const [tasksRes, wgRes] = await Promise.all([
            fetch(`${API_BASE}/tasks/`, { headers }),
            fetch(`${API_BASE}/workgroups/`, { headers })
        ]);
        if (!tasksRes.ok) { if (tasksRes.status === 401) { localStorage.removeItem('authToken'); authToken = null; showLogin(); } return; }
        const tasks = await tasksRes.json();
        const workgroups = wgRes.ok ? await wgRes.json() : [];
        lastTimelineData = { tasks, workgroups };
        renderTimeline(tasks, workgroups);
    } catch (e) { console.error('Ошибка загрузки таймлайна:', e); }
}

function renderTimeline(tasks, workgroups) {
    const container = document.getElementById('timeline-list');
    const filterEl = document.getElementById('timeline-wg-filter');
    const wgId = filterEl ? filterEl.value : '';
    let filtered = tasks;
    if (wgId) filtered = tasks.filter(t => t.workgroup_id === parseInt(wgId, 10));

    if (filterEl) {
        filterEl.innerHTML = '<option value="">Все</option>' + workgroups.map(wg =>
            `<option value="${wg.id}" ${wgId == wg.id ? 'selected' : ''}>${wg.name}</option>`
        ).join('');
        filterEl.onchange = () => renderTimeline(lastTimelineData.tasks, lastTimelineData.workgroups);
    }

    container.innerHTML = filtered.map((task, idx) => {
        const assignees = (task.assignees || []).map(a => a.full_name || a.username || a.login || 'ID ' + a.id).join(', ');
        const assigneeTip = (assignees || 'Исполнители не назначены').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
        const createdStr = task.created_at ? formatDate(task.created_at) : '—';
        const dueStr = task.due_date ? formatDate(task.due_date) : '—';
        const pollResponses = (task.poll_responses || []).sort((a, b) => new Date(a.polled_at) - new Date(b.polled_at));
        const n = pollResponses.length;
        const isDone = task.status === 'done';

        function escapeAttr(str) {
            return (str || '').replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        }
        function buildResponseTooltip(pr) {
            const pollDate = formatDate(pr.polled_at);
            const userName = (pr.user && (pr.user.full_name || pr.user.username || pr.user.login)) || 'Исполнитель';
            const answer = (pr.response_text || '').trim();
            return answer
                ? `${pollDate}: ${userName} — «${answer}»`
                : `${pollDate}: ${userName} — опрошен, ответа нет`;
        }

        let dotsHtml = pollResponses.map((pr, i) => {
            const isLast = i === n - 1;
            const pct = getDotPositionPercent(i, n, isDone);
            const cls = isLast ? (isDone ? 'timeline-bar-dot active timeline-bar-dot-done' : 'timeline-bar-dot active') : 'timeline-bar-dot response';
            const tooltip = buildResponseTooltip(pr);
            const tipSafe = escapeAttr(tooltip);
            return `<span class="${cls}" style="left:${pct}%" data-tooltip="${tipSafe}" title="${tipSafe}"> </span>`;
        }).join('');
        if (isDone && n === 0) {
            dotsHtml = `<span class="timeline-bar-dot active timeline-bar-dot-done" style="left:100%" title="Выполнена"> </span>`;
        }

        const lineClass = isDone ? 'timeline-track-line timeline-track-line--done' : 'timeline-track-line';
        const labelsHtml = TIMELINE_ZONES.map(z => `<span style="flex:${z.pct / 100}">${z.label}</span>`).join('');

        return `
        <div class="timeline-item" onclick="editTask(${task.id})" style="cursor:pointer; animation-delay: ${idx * 50}ms">
            <div class="timeline-item-header">
                <span class="timeline-item-title">${task.title}</span>
                <span class="timeline-item-meta">${assignees ? 'Исп.: ' + assignees : ''} <button type="button" class="timeline-nudge-btn" onclick="event.stopPropagation(); nudgeTask(${task.id})" title="Напомнить в Telegram">Тыкнуть</button></span>
            </div>
            <div class="timeline-bar">
                <span class="timeline-date">${createdStr}</span>
                <div class="timeline-track">
                    <div class="${lineClass}" role="presentation"></div>
                    ${dotsHtml}
                </div>
                <span class="timeline-date timeline-date-end">${dueStr}</span>
            </div>
            <div class="timeline-bar-labels timeline-bar-labels-zones">${labelsHtml}</div>
        </div>
        `;
    }).join('') || '<p class="text-center" style="color:var(--secondary-color)">Нет задач</p>';
}

// Загрузка рабочих групп
async function loadWorkgroups() {
    const headers = getAuthHeaders();
    if (!headers) { showLogin(); return; }
    try {
        const response = await fetch(`${API_BASE}/workgroups/`, { headers });
        
        if (response.ok) {
            const workgroups = await response.json();
            renderWorkgroups(workgroups);
        } else if (response.status === 401) {
            localStorage.removeItem('authToken');
            authToken = null;
            showLogin();
        }
    } catch (error) {
        console.error('Ошибка загрузки групп:', error);
    }
}

// Отображение рабочих групп
function renderWorkgroups(workgroups) {
    const container = document.getElementById('workgroups-list');
    container.innerHTML = workgroups.map((wg, i) => {
        const resp = wg.responsible ? (wg.responsible.full_name || wg.responsible.login || 'ID ' + wg.responsible.id) : 'Не назначен';
        return `
        <div class="card" style="animation-delay: ${i * 50}ms">
            <div class="card-title">${wg.name}</div>
            <div class="card-description">${wg.description || 'Без описания'}</div>
            <div class="card-meta"><span class="badge badge-primary">Ответственный: ${resp}</span></div>
            <div class="card-actions">
                <button class="btn btn-sm btn-primary" onclick="editWorkgroup(${wg.id})">Редактировать</button>
                <button class="btn btn-sm btn-danger" onclick="deleteWorkgroup(${wg.id})">Удалить</button>
            </div>
        </div>`;
    }).join('');
}

// Загрузка пользователей
async function loadUsers() {
    const headers = getAuthHeaders();
    if (!headers) { showLogin(); return; }
    try {
        const response = await fetch(`${API_BASE}/users/`, { headers });
        
        if (response.ok) {
            const users = await response.json();
            renderUsers(users);
        } else if (response.status === 401) {
            localStorage.removeItem('authToken');
            authToken = null;
            showLogin();
        }
    } catch (error) {
        console.error('Ошибка загрузки пользователей:', error);
    }
}

// Отображение пользователей
function renderUsers(users) {
    const container = document.getElementById('users-list');
    container.innerHTML = users.map((user, i) => `
        <div class="card" style="animation-delay: ${i * 50}ms">
            <div class="card-title">${user.full_name || user.username || user.login || 'Без имени'}</div>
            <div class="card-description">Роль: ${getRoleText(user.role)}</div>
            <div class="card-meta">
                <span class="badge badge-primary">${user.login || 'Нет логина'}</span>
                ${user.username ? `<span class="badge badge-primary">@${user.username}</span>` : ''}
                ${user.telegram_id ? `<span class="badge badge-success" title="Получает уведомления">TG ✓</span>` : ''}
            </div>
            <div class="card-actions">
                <button class="btn btn-sm btn-primary" onclick="editUser(${user.id})">Редактировать</button>
            </div>
        </div>
    `).join('');
}

// Шоб не забыть — заметки (localStorage)
const NOTES_KEY = 'tasktracker_notes';
const STICKY_COLORS = ['sticky-yellow', 'sticky-pink', 'sticky-blue', 'sticky-green', 'sticky-orange', 'sticky-lavender'];

function getNotes() {
    try {
        const raw = localStorage.getItem(NOTES_KEY);
        return raw ? JSON.parse(raw) : [];
    } catch (_) { return []; }
}

function saveNotes(notes) {
    localStorage.setItem(NOTES_KEY, JSON.stringify(notes));
}

function addStickyNote() {
    const notes = getNotes();
    const color = STICKY_COLORS[notes.length % STICKY_COLORS.length];
    const newNote = {
        id: Date.now().toString(36) + Math.random().toString(36).slice(2),
        text: '',
        color,
        createdAt: Date.now()
    };
    notes.push(newNote);
    saveNotes(notes);
    renderStickyNotes();
}

function updateStickyNote(id, text) {
    const notes = getNotes();
    const n = notes.find(x => x.id === id);
    if (n) {
        n.text = text;
        n.updatedAt = Date.now();
        saveNotes(notes);
    }
}

function deleteStickyNote(id) {
    const notes = getNotes().filter(n => n.id !== id);
    saveNotes(notes);
    renderStickyNotes();
}

function autoResizeStickyTextarea(ta) {
    ta.style.height = 'auto';
    ta.style.height = Math.max(40, ta.scrollHeight) + 'px';
}

function renderStickyNotes() {
    const container = document.getElementById('notes-board');
    if (!container) return;

    const notes = getNotes();

    const html = notes.map((note, i) => `
        <div class="sticky-note ${note.color}" style="animation-delay: ${i * 40}ms" data-id="${note.id}">
            <div class="sticky-text">
                <textarea class="sticky-textarea" placeholder="Напишите заметку..." onblur="updateStickyNote('${note.id}', this.value)" oninput="autoResizeStickyTextarea(this)">${escapeHtml(note.text)}</textarea>
            </div>
            <div class="sticky-actions">
                <button type="button" onclick="deleteStickyNote('${note.id}')" title="Удалить">Удалить</button>
            </div>
        </div>
    `).join('') + `
        <div class="sticky-note add-new" onclick="addStickyNote()" title="Добавить заметку" style="animation-delay: ${notes.length * 40}ms">
            <span style="font-size: 2rem; margin-bottom: 0.5rem">+</span>
            <span>Новая заметка</span>
        </div>
    `;

    container.innerHTML = html;
    container.querySelectorAll('.sticky-textarea').forEach(autoResizeStickyTextarea);
}

function escapeHtml(s) {
    if (!s) return '';
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}

// Модальные окна
function showModal(title, content) {
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-body').innerHTML = content;
    document.getElementById('modal-overlay').style.display = 'flex';
}

function closeModal() {
    document.getElementById('modal-overlay').style.display = 'none';
}

// Создание задачи
async function showCreateTaskModal() {
    const authHeaders = getAuthHeaders();
    if (!authHeaders) { alert('Сессия истекла.'); showLogin(); return; }
    
    let workgroups = [], assignableUsers = [];
    try {
        const [wgRes, usersRes] = await Promise.all([
            fetch(`${API_BASE}/workgroups/`, { headers: authHeaders }),
            fetch(`${API_BASE}/tasks/assignable-users`, { headers: authHeaders })
        ]);
        if (wgRes.ok) workgroups = await wgRes.json();
        if (usersRes.ok) assignableUsers = await usersRes.json();
    } catch (e) { console.error(e); }
    
    const wgOptions = workgroups.map(wg =>
        `<option value="${wg.id}">${wg.name}</option>`
    ).join('');
    const assigneeCheckboxes = assignableUsers.map(u =>
        `<label class="checkbox-label"><input type="checkbox" name="assignee" value="${u.id}"> ${u.full_name || u.username || u.login || 'ID ' + u.id} (${getRoleText(u.role)})</label>`
    ).join('') || '<em>Нет доступных пользователей. Выберите рабочую группу.</em>';
    
    const content = `
        <form id="create-task-form">
            <div class="form-group">
                <label>Название</label>
                <input type="text" name="title" required>
            </div>
            <div class="form-group">
                <label>Описание</label>
                <textarea name="description"></textarea>
            </div>
            <div class="form-group">
                <label>Рабочая группа</label>
                <select name="workgroup_id" id="create-task-wg">
                    <option value="">— Без группы —</option>
                    ${wgOptions}
                </select>
            </div>
            <div class="form-group">
                <label>Исполнители (отметьте галочками)</label>
                <div class="checkbox-group" id="create-task-assignees">${assigneeCheckboxes}</div>
            </div>
            <div class="form-group">
                <label>Срок (ДДЛ)</label>
                <input type="datetime-local" name="due_date">
            </div>
            <div class="form-group">
                <label>Опрос о задаче (напоминания в Telegram)</label>
                <div class="poll-settings">
                    <div><label>Как часто:</label> каждые <input type="number" name="poll_interval_days" min="1" placeholder="дней" style="width:70px"> дней</div>
                    <div><label>Во сколько:</label> <input type="time" name="poll_time" style="width:110px" placeholder="09:00"></div>
                </div>
                <small style="color:var(--secondary-color)">Оставьте пустым, чтобы отключить опрос</small>
            </div>
            <div class="form-group">
                <label>Статус</label>
                <select name="status">
                    <option value="new">Новая</option>
                    <option value="in_progress">В работе</option>
                    <option value="review">На проверке</option>
                    <option value="done">Выполнена</option>
                </select>
            </div>
            <button type="submit" class="btn btn-primary">Создать</button>
        </form>
    `;
    showModal('Создать задачу', content);
    
    document.getElementById('create-task-wg')?.addEventListener('change', async (e) => {
        const wgId = e.target.value;
        if (!wgId) return;
        try {
            const res = await fetch(`${API_BASE}/tasks/assignable-users?workgroup_id=${wgId}`, { headers: authHeaders });
            const users = res.ok ? await res.json() : [];
            const html = users.map(u =>
                `<label class="checkbox-label"><input type="checkbox" name="assignee" value="${u.id}"> ${u.full_name || u.username || u.login || 'ID ' + u.id} (${getRoleText(u.role)})</label>`
            ).join('') || '<em>В группе нет участников</em>';
            document.getElementById('create-task-assignees').innerHTML = html;
        } catch (err) { console.error(err); }
    });
    
    document.getElementById('create-task-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const assigneeIds = formData.getAll('assignee').map(id => parseInt(id, 10)).filter(id => !isNaN(id));
        const dueVal = formData.get('due_date');
        const pollInterval = formData.get('poll_interval_days');
        const pollVal = parseInt(pollInterval, 10);
        const taskData = {
            title: formData.get('title'),
            description: formData.get('description'),
            status: formData.get('status'),
            workgroup_id: formData.get('workgroup_id') ? parseInt(formData.get('workgroup_id'), 10) : null,
            assignee_ids: assigneeIds,
            due_date: dueVal ? new Date(dueVal).toISOString() : null,
            poll_interval_days: (pollInterval && !isNaN(pollVal) && pollVal > 0) ? pollVal : null,
            poll_time: formData.get('poll_time') || null
        };
        
        try {
            if (!authHeaders) { alert('Сессия истекла. Войдите снова.'); closeModal(); showLogin(); return; }
            const response = await fetch(`${API_BASE}/tasks/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...authHeaders },
                body: JSON.stringify(taskData)
            });
            
            if (response.ok) {
                closeModal();
                await loadTasks();
                loadTimeline();
            } else {
                const error = await response.json();
                alert('Ошибка: ' + (error.detail || JSON.stringify(error)));
            }
        } catch (error) {
            console.error('Ошибка создания задачи:', error);
            alert('Ошибка создания задачи');
        }
    });
}

// Редактирование задачи
async function editTask(taskId) {
    const authHeaders = getAuthHeaders();
    if (!authHeaders) { alert('Сессия истекла.'); showLogin(); return; }
    
    let task, workgroups = [], assignableUsers = [];
    try {
        const taskRes = await fetch(`${API_BASE}/tasks/${taskId}`, { headers: authHeaders });
        if (!taskRes.ok) { alert('Задача не найдена'); return; }
        task = await taskRes.json();
        const [wgRes, uRes] = await Promise.all([
            fetch(`${API_BASE}/workgroups/`, { headers: authHeaders }),
            fetch(`${API_BASE}/tasks/assignable-users${task.workgroup_id ? `?workgroup_id=${task.workgroup_id}` : ''}`, { headers: authHeaders })
        ]);
        if (wgRes.ok) workgroups = await wgRes.json();
        if (uRes.ok) assignableUsers = await uRes.json();
    } catch (e) { console.error(e); alert('Ошибка загрузки'); return; }
    
    const assigneeIds = new Set(task.assignee_ids || (task.assignee ? [task.assignee.id] : []));
    const wgOptions = workgroups.map(wg =>
        `<option value="${wg.id}" ${task.workgroup_id === wg.id ? 'selected' : ''}>${wg.name}</option>`
    ).join('');
    const assigneeCheckboxes = assignableUsers.map(u =>
        `<label class="checkbox-label"><input type="checkbox" name="assignee" value="${u.id}" ${assigneeIds.has(u.id) ? 'checked' : ''}> ${u.full_name || u.username || u.login || 'ID ' + u.id} (${getRoleText(u.role)})</label>`
    ).join('') || '<em>Нет доступных пользователей</em>';
    
    const content = `
        <form id="edit-task-form">
            <div class="form-group">
                <label>Название</label>
                <input type="text" name="title" value="${(task.title || '').replace(/"/g, '&quot;')}" required>
            </div>
            <div class="form-group">
                <label>Описание</label>
                <textarea name="description">${(task.description || '').replace(/</g, '&lt;')}</textarea>
            </div>
            <div class="form-group">
                <label>Рабочая группа</label>
                <select name="workgroup_id" id="edit-task-wg">
                    <option value="">— Без группы —</option>
                    ${wgOptions}
                </select>
            </div>
            <div class="form-group">
                <label>Исполнители (отметьте галочками)</label>
                <div class="checkbox-group" id="edit-task-assignees">${assigneeCheckboxes}</div>
            </div>
            <div class="form-group">
                <label>Срок (ДДЛ)</label>
                <input type="datetime-local" name="due_date" value="${task.due_date ? new Date(task.due_date).toISOString().slice(0, 16) : ''}">
            </div>
            <div class="form-group">
                <label>Опрос о задаче (напоминания в Telegram)</label>
                <div class="poll-settings">
                    <div><label>Как часто:</label> каждые <input type="number" name="poll_interval_days" min="1" value="${task.poll_interval_days || ''}" placeholder="дней" style="width:70px"> дней</div>
                    <div><label>Во сколько:</label> <input type="time" name="poll_time" value="${task.poll_time || ''}" style="width:110px"></div>
                </div>
                <small style="color:var(--secondary-color)">Оставьте пустым, чтобы отключить опрос</small>
            </div>
            <div class="form-group">
                <label>Статус</label>
                <select name="status">
                    <option value="new" ${task.status === 'new' ? 'selected' : ''}>Новая</option>
                    <option value="in_progress" ${task.status === 'in_progress' ? 'selected' : ''}>В работе</option>
                    <option value="review" ${task.status === 'review' ? 'selected' : ''}>На проверке</option>
                    <option value="done" ${task.status === 'done' ? 'selected' : ''}>Выполнена</option>
                </select>
            </div>
            <button type="submit" class="btn btn-primary">Сохранить</button>
        </form>
    `;
    showModal('Редактировать задачу', content);
    
    document.getElementById('edit-task-wg')?.addEventListener('change', async (e) => {
        const wgId = e.target.value;
        try {
            const url = wgId ? `${API_BASE}/tasks/assignable-users?workgroup_id=${wgId}` : `${API_BASE}/tasks/assignable-users`;
            const res = await fetch(url, { headers: authHeaders });
            const users = res.ok ? await res.json() : [];
            const ids = new Set(assigneeIds);
            const html = users.map(u =>
                `<label class="checkbox-label"><input type="checkbox" name="assignee" value="${u.id}" ${ids.has(u.id) ? 'checked' : ''}> ${u.full_name || u.username || u.login || 'ID ' + u.id} (${getRoleText(u.role)})</label>`
            ).join('') || '<em>В группе нет участников</em>';
            document.getElementById('edit-task-assignees').innerHTML = html;
        } catch (err) { console.error(err); }
    });
    
    document.getElementById('edit-task-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const assigneeIdsList = formData.getAll('assignee').map(id => parseInt(id, 10)).filter(id => !isNaN(id));
        const dueVal = formData.get('due_date');
        const pollInterval = formData.get('poll_interval_days');
        const pollVal = parseInt(pollInterval, 10);
        const updateData = {
            title: formData.get('title'),
            description: formData.get('description'),
            status: formData.get('status'),
            workgroup_id: formData.get('workgroup_id') ? parseInt(formData.get('workgroup_id'), 10) : null,
            assignee_ids: assigneeIdsList,
            due_date: dueVal ? new Date(dueVal).toISOString() : null,
            poll_interval_days: (pollInterval && !isNaN(pollVal) && pollVal > 0) ? pollVal : null,
            poll_time: formData.get('poll_time') || null
        };
        try {
            const res = await fetch(`${API_BASE}/tasks/${taskId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json', ...authHeaders },
                body: JSON.stringify(updateData)
            });
            if (res.ok) {
                closeModal();
                await loadTasks();
                loadTimeline();
            } else { const err = await res.json(); alert('Ошибка: ' + (err.detail || JSON.stringify(err))); }
        } catch (err) { alert('Ошибка сохранения'); }
    });
}

// Создание рабочей группы
async function showCreateWorkgroupModal() {
    const authHeaders = getAuthHeaders();
    if (!authHeaders) { alert('Сессия истекла.'); showLogin(); return; }
    
    let assignableUsers = [];
    try {
        const res = await fetch(`${API_BASE}/users/assignable`, { headers: authHeaders });
        if (res.ok) assignableUsers = await res.json();
    } catch (e) { console.error('Ошибка загрузки пользователей:', e); }
    
    const responsibleOptions = assignableUsers.map(u => 
        `<option value="${u.id}">${u.full_name || u.username || u.login || 'ID ' + u.id} (${getRoleText(u.role)})</option>`
    ).join('');
    
    const memberOptions = assignableUsers.map(u => 
        `<label class="checkbox-label"><input type="checkbox" name="member" value="${u.id}"> ${u.full_name || u.username || u.login || 'ID ' + u.id} (${getRoleText(u.role)})</label>`
    ).join('');
    
    const content = `
        <form id="create-workgroup-form">
            <div class="form-group">
                <label>Название</label>
                <input type="text" name="name" required>
            </div>
            <div class="form-group">
                <label>Описание</label>
                <textarea name="description"></textarea>
            </div>
            <div class="form-group">
                <label>Ответственный за группу</label>
                <select name="responsible_id">
                    <option value="">— Не назначен —</option>
                    ${responsibleOptions}
                </select>
            </div>
            <div class="form-group">
                <label>Участники группы</label>
                <div class="checkbox-group">${memberOptions || '<em>Нет доступных пользователей</em>'}</div>
            </div>
            <button type="submit" class="btn btn-primary">Создать</button>
        </form>
    `;
    showModal('Создать рабочую группу', content);
    
    document.getElementById('create-workgroup-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const memberIds = formData.getAll('member').map(id => parseInt(id, 10)).filter(id => !isNaN(id));
        const responsibleId = formData.get('responsible_id') || null;
        const workgroupData = {
            name: formData.get('name'),
            description: formData.get('description'),
            responsible_id: responsibleId ? parseInt(responsibleId, 10) : null,
            member_ids: memberIds
        };
        
        try {
            const authHeaders = getAuthHeaders();
            if (!authHeaders) { alert('Сессия истекла. Войдите снова.'); closeModal(); showLogin(); return; }
            const response = await fetch(`${API_BASE}/workgroups/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...authHeaders },
                body: JSON.stringify(workgroupData)
            });
            
            if (response.ok) {
                closeModal();
                await loadWorkgroups();
            } else {
                const error = await response.json();
                alert('Ошибка: ' + error.detail);
            }
        } catch (error) {
            console.error('Ошибка создания группы:', error);
            alert('Ошибка создания группы');
        }
    });
}

// Редактирование рабочей группы
async function editWorkgroup(id) {
    const authHeaders = getAuthHeaders();
    if (!authHeaders) { alert('Сессия истекла.'); showLogin(); return; }
    
    let wg, assignableUsers = [];
    try {
        const [wgRes, usersRes] = await Promise.all([
            fetch(`${API_BASE}/workgroups/${id}`, { headers: authHeaders }),
            fetch(`${API_BASE}/users/assignable`, { headers: authHeaders })
        ]);
        if (!wgRes.ok) { alert('Группа не найдена'); return; }
        wg = await wgRes.json();
        if (usersRes.ok) assignableUsers = await usersRes.json();
    } catch (e) { console.error(e); alert('Ошибка загрузки'); return; }
    
    const memberIds = new Set((wg.members || []).map(m => m.id));
    const responsibleOptions = assignableUsers.map(u => 
        `<option value="${u.id}" ${wg.responsible_id === u.id ? 'selected' : ''}>${u.full_name || u.username || u.login || 'ID ' + u.id} (${getRoleText(u.role)})</option>`
    ).join('');
    const memberOptions = assignableUsers.map(u => 
        `<label class="checkbox-label"><input type="checkbox" name="member" value="${u.id}" ${memberIds.has(u.id) ? 'checked' : ''}> ${u.full_name || u.username || u.login || 'ID ' + u.id} (${getRoleText(u.role)})</label>`
    ).join('');
    
    const content = `
        <form id="edit-workgroup-form">
            <div class="form-group">
                <label>Название</label>
                <input type="text" name="name" value="${(wg.name || '').replace(/"/g, '&quot;')}" required>
            </div>
            <div class="form-group">
                <label>Описание</label>
                <textarea name="description">${(wg.description || '').replace(/</g, '&lt;')}</textarea>
            </div>
            <div class="form-group">
                <label>Ответственный за группу</label>
                <select name="responsible_id">
                    <option value="">— Не назначен —</option>
                    ${responsibleOptions}
                </select>
            </div>
            <div class="form-group">
                <label>Участники группы</label>
                <div class="checkbox-group">${memberOptions || '<em>Нет доступных пользователей</em>'}</div>
            </div>
            <button type="submit" class="btn btn-primary">Сохранить</button>
        </form>
    `;
    showModal('Редактировать рабочую группу', content);
    
    document.getElementById('edit-workgroup-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const memberIds = formData.getAll('member').map(i => parseInt(i, 10)).filter(i => !isNaN(i));
        const rawResp = formData.get('responsible_id');
        const updateData = {
            name: formData.get('name'),
            description: formData.get('description'),
            responsible_id: rawResp ? parseInt(rawResp, 10) : 0,
            member_ids: memberIds
        };
        try {
            const res = await fetch(`${API_BASE}/workgroups/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json', ...authHeaders },
                body: JSON.stringify(updateData)
            });
            if (res.ok) {
                closeModal();
                await loadWorkgroups();
            } else { const err = await res.json(); alert('Ошибка: ' + err.detail); }
        } catch (err) { console.error(err); alert('Ошибка сохранения'); }
    });
}

// Создание пользователя
function showCreateUserModal() {
    const content = `
        <form id="create-user-form">
            <div class="form-group">
                <label>Логин</label>
                <input type="text" name="login" placeholder="Для входа в веб (обязателен для ролей с доступом к сайту)">
            </div>
            <div class="form-group">
                <label>Пароль</label>
                <input type="password" name="password" required>
            </div>
            <div class="form-group">
                <label>Имя</label>
                <input type="text" name="full_name">
            </div>
            <div class="form-group">
                <label>Telegram @username</label>
                <input type="text" name="username" placeholder="@username без @">
            </div>
            <div class="form-group">
                <label>Telegram ID (числовой)</label>
                <input type="number" name="telegram_id" placeholder="Для уведомлений в боте">
            </div>
            <div class="form-group">
                <label>Роль</label>
                <select name="role">
                    <option value="main_organizer">Главный организатор</option>
                    <option value="responsible">Ответственный</option>
                    <option value="worker">Работник</option>
                    <option value="project_manager">Проектник</option>
                </select>
            </div>
            <button type="submit" class="btn btn-primary">Создать</button>
        </form>
    `;
    showModal('Создать пользователя', content);
    
    document.getElementById('create-user-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const tgId = formData.get('telegram_id');
        const userData = {
            login: formData.get('login'),
            password: formData.get('password'),
            full_name: formData.get('full_name'),
            username: formData.get('username') ? (formData.get('username').replace(/^@/, '') || null) : null,
            telegram_id: tgId ? parseInt(tgId, 10) : null,
            role: formData.get('role')
        };
        
        try {
            const authHeaders = getAuthHeaders();
            if (!authHeaders) { alert('Сессия истекла. Войдите снова.'); closeModal(); showLogin(); return; }
            const response = await fetch(`${API_BASE}/users/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...authHeaders },
                body: JSON.stringify(userData)
            });
            
            if (response.ok) {
                closeModal();
                await loadUsers();
            } else {
                if (response.status === 401) {
                    localStorage.removeItem('authToken');
                    authToken = null;
                    closeModal();
                    showLogin();
                    alert('Сессия истекла. Войдите снова.');
                } else {
                    const error = await response.json();
                    alert('Ошибка: ' + (error.detail || 'Не удалось создать пользователя'));
                }
            }
        } catch (error) {
            console.error('Ошибка создания пользователя:', error);
            alert('Ошибка создания пользователя');
        }
    });
}

// Редактирование пользователя (установить логин/пароль)
async function editUser(id) {
    const authHeaders = getAuthHeaders();
    if (!authHeaders) { alert('Сессия истекла.'); showLogin(); return; }
    let user;
    try {
        const res = await fetch(`${API_BASE}/users/${id}`, { headers: authHeaders });
        if (!res.ok) { alert('Пользователь не найден'); return; }
        user = await res.json();
    } catch (e) { alert('Ошибка загрузки'); return; }
    
    const content = `
        <form id="edit-user-form">
            <div class="form-group">
                <label>Логин</label>
                <input type="text" name="login" value="${(user.login || '').replace(/"/g, '&quot;')}" placeholder="Нужен для входа в веб">
            </div>
            <div class="form-group">
                <label>Новый пароль</label>
                <input type="password" name="password" placeholder="Оставьте пустым, чтобы не менять">
            </div>
            <div class="form-group">
                <label>Имя</label>
                <input type="text" name="full_name" value="${(user.full_name || '').replace(/"/g, '&quot;')}">
            </div>
            <div class="form-group">
                <label>Telegram @username</label>
                <input type="text" name="username" value="${(user.username || '').replace(/"/g, '&quot;')}" placeholder="@username без @">
            </div>
            <div class="form-group">
                <label>Telegram ID (числовой)</label>
                <input type="number" name="telegram_id" value="${user.telegram_id || ''}" placeholder="Для уведомлений в боте">
            </div>
            <div class="form-group">
                <label>Роль</label>
                <select name="role">
                    <option value="main_organizer" ${user.role === 'main_organizer' ? 'selected' : ''}>Главный организатор</option>
                    <option value="responsible" ${user.role === 'responsible' ? 'selected' : ''}>Ответственный</option>
                    <option value="worker" ${user.role === 'worker' ? 'selected' : ''}>Работник</option>
                    <option value="project_manager" ${user.role === 'project_manager' ? 'selected' : ''}>Проектник</option>
                </select>
            </div>
            <button type="submit" class="btn btn-primary">Сохранить</button>
        </form>
    `;
    showModal('Редактировать пользователя', content);
    
    document.getElementById('edit-user-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const tgId = formData.get('telegram_id');
        const updateData = {
            login: formData.get('login') || null,
            full_name: formData.get('full_name') || null,
            username: formData.get('username') ? (formData.get('username').replace(/^@/, '') || null) : null,
            telegram_id: tgId ? parseInt(tgId, 10) : null,
            role: formData.get('role')
        };
        if (formData.get('password')) updateData.password = formData.get('password');
        try {
            const res = await fetch(`${API_BASE}/users/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json', ...authHeaders },
                body: JSON.stringify(updateData)
            });
            if (res.ok) {
                closeModal();
                await loadUsers();
            } else { const err = await res.json(); alert('Ошибка: ' + err.detail); }
        } catch (err) { alert('Ошибка сохранения'); }
    });
}

// Утилиты
function formatDate(isoStr) {
    if (!isoStr) return '';
    const d = new Date(isoStr);
    return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

function getStatusText(status) {
    const statusMap = {
        'new': 'Новая',
        'in_progress': 'В работе',
        'review': 'На проверке',
        'done': 'Выполнена',
        'cancelled': 'Отменена'
    };
    return statusMap[status] || status;
}

function getStatusColor(status) {
    const colorMap = {
        'new': 'primary',
        'in_progress': 'warning',
        'review': 'warning',
        'done': 'success',
        'cancelled': 'danger'
    };
    return colorMap[status] || 'primary';
}

function getRoleText(role) {
    const roleMap = {
        'project_manager': 'Проектник',
        'main_organizer': 'Главный организатор',
        'responsible': 'Ответственный',
        'worker': 'Работник'
    };
    return roleMap[role] || role;
}

// Удаление задач
async function nudgeTask(taskId) {
    const headers = getAuthHeaders();
    if (!headers) { showLogin(); return; }
    try {
        const res = await fetch(`${API_BASE}/tasks/${taskId}/nudge`, { method: 'POST', headers });
        const data = await res.json().catch(() => ({}));
        if (res.ok && data.ok) {
            alert(data.message || 'Напоминание отправлено');
            if (document.querySelector('.tab-btn.active')?.dataset.tab === 'timeline') loadTimeline();
        } else {
            alert(data.message || 'Не удалось отправить напоминание');
        }
    } catch (e) {
        alert('Ошибка отправки');
    }
}

async function deleteTask(taskId) {
    if (!confirm('Удалить задачу?')) return;
    
    try {
        const headers = getAuthHeaders();
        if (!headers) { showLogin(); return; }
        const response = await fetch(`${API_BASE}/tasks/${taskId}`, {
            method: 'DELETE',
            headers
        });
        
        if (response.ok) {
            await loadTasks();
            loadTimeline();
        } else {
            const error = await response.json();
            alert('Ошибка: ' + error.detail);
        }
    } catch (error) {
        console.error('Ошибка удаления задачи:', error);
    }
}

// Удаление рабочих групп
async function deleteWorkgroup(workgroupId) {
    if (!confirm('Удалить рабочую группу?')) return;
    
    try {
        const headers = getAuthHeaders();
        if (!headers) { showLogin(); return; }
        const response = await fetch(`${API_BASE}/workgroups/${workgroupId}`, {
            method: 'DELETE',
            headers
        });
        
        if (response.ok) {
            await loadWorkgroups();
        } else {
            const error = await response.json();
            alert('Ошибка: ' + error.detail);
        }
    } catch (error) {
        console.error('Ошибка удаления группы:', error);
    }
}

// Закрытие модального окна: только клик по overlay или Escape (не от Ctrl+C/Ctrl+V)
document.getElementById('modal-overlay')?.addEventListener('click', (e) => {
    if (e.target.id === 'modal-overlay') {
        closeModal();
    }
});

document.addEventListener('keydown', (e) => {
    const overlay = document.getElementById('modal-overlay');
    const isOpen = overlay && overlay.style.display === 'flex';
    if (!isOpen) return;
    if (e.key === 'Escape') {
        closeModal();
        e.preventDefault();
        return;
    }
    // Не даём Ctrl+C / Ctrl+V пробрасываться — чтобы случайный обработчик не закрыл модалку
    if ((e.ctrlKey || e.metaKey) && (e.key.toLowerCase() === 'c' || e.key.toLowerCase() === 'v')) {
        e.stopPropagation();
    }
}, true);

// Обновление данных в реальном времени: раз в 25 сек перезагружаем активную вкладку (только если пользователь залогинен)
const REFRESH_INTERVAL_MS = 25000;
setInterval(() => {
    if (getAuthHeaders()) loadData();
}, REFRESH_INTERVAL_MS);
