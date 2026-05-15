document.addEventListener('DOMContentLoaded', () => {
    // 1. Initial State
    let boardState = JSON.parse(localStorage.getItem('uniplan_state')) || {
        pool: COURSE_DATA.map(c => c.id),
        semesters: {
            "1": [],
            "2": [],
            "3": [],
            "4": []
        },
        difficulties: {} // id -> "Low" | "Medium" | "High"
    };

    const courseMap = {};
    COURSE_DATA.forEach(c => {
        courseMap[c.id] = c;
    });

    // Clean up boardState (in case COURSE_DATA changed)
    const validIds = new Set(COURSE_DATA.map(c => c.id));
    boardState.pool = boardState.pool.filter(id => validIds.has(id));
    for (let s in boardState.semesters) {
        boardState.semesters[s] = boardState.semesters[s].filter(id => validIds.has(id));
    }

    // Identify courses missing from boardState (new courses)
    const storedIds = new Set([
        ...boardState.pool,
        ...boardState.semesters["1"],
        ...boardState.semesters["2"],
        ...boardState.semesters["3"],
        ...boardState.semesters["4"]
    ]);

    COURSE_DATA.forEach(c => {
        if (!storedIds.has(c.id)) {
            boardState.pool.push(c.id);
        }
    });


    // 2. DOM Elements
    const poolContainer = document.getElementById('poolContainer');
    const boardContainer = document.getElementById('boardContainer');
    const searchInput = document.getElementById('searchInput');
    const filterPills = document.getElementById('filterPills');
    const resetBtn = document.getElementById('resetBtn');

    // Modal Elements
    const modal = document.getElementById('courseModal');
    const modalId = document.getElementById('modalId');
    const modalTitle = document.getElementById('modalTitle');
    const modalEcts = document.getElementById('modalEcts');
    const modalDate = document.getElementById('modalDate');
    const modalProf = document.getElementById('modalProf');
    const modalPillar = document.getElementById('modalPillar');
    const modalDesc = document.getElementById('modalDesc');
    const closeModalBtn = document.getElementById('closeModalBtn');

    let currentFilter = 'all';

    // 3. Render Functions
    function createCard(id) {
        const course = courseMap[id];
        if (!course) return null;

        const diff = boardState.difficulties[id] || course.defaultDifficulty || 'Medium';

        const card = document.createElement('div');
        card.className = `course-card p-3 rounded-lg flex flex-col gap-2`;
        card.dataset.id = id;

        card.innerHTML = `
            <div class="diff-bar diff-bg-${diff}"></div>
            <div class="flex justify-between items-start ml-2">
                <div class="flex flex-col gap-1">
                    <div class="text-xs text-brand-500 font-mono">${id}</div>
                    ${course.pillar !== 'General' ? `<div class="text-[9px] text-gray-400 bg-gray-800/80 px-1 py-0.5 rounded border border-gray-600/50 inline-block w-max max-w-[150px] truncate" title="${course.pillar} - ${course.type}">${course.pillar} <span class="text-brand-500">•</span> ${course.type}</div>` : ''}
                </div>
                <button class="diff-toggle text-[10px] font-semibold px-1.5 py-0.5 rounded bg-dark-bg/50 diff-text-${diff} hover:bg-dark-bg transition-colors" data-id="${id}">${diff}</button>
            </div>
            <div class="text-sm font-semibold text-gray-200 ml-2 leading-snug line-clamp-2 mt-1" title="${course.name}">${course.name}</div>
            <div class="flex justify-between items-center ml-2 mt-2">
                <div class="text-[10px] text-gray-400 flex items-center gap-1">
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>
                    ${course.examDate || 'TBA'}
                </div>
                <div class="text-xs font-bold text-gray-300 bg-gray-700 px-1.5 py-0.5 rounded">${course.ects} ECTS</div>
            </div>
        `;

        // Details Button (Double click on card also works)
        card.addEventListener('dblclick', () => showModal(id));

        // Difficulty Toggle
        const diffBtn = card.querySelector('.diff-toggle');
        diffBtn.addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent drag
            toggleDifficulty(id, card, diffBtn);
        });

        return card;
    }

    function toggleDifficulty(id, card, btn) {
        const levels = ['Low', 'Medium', 'High'];
        let current = boardState.difficulties[id] || courseMap[id].defaultDifficulty || 'Medium';
        let next = levels[(levels.indexOf(current) + 1) % levels.length];

        boardState.difficulties[id] = next;
        saveState();

        // Update UI
        const bar = card.querySelector('.diff-bar');
        levels.forEach(l => {
            bar.classList.remove(`diff-bg-${l}`);
            btn.classList.remove(`diff-text-${l}`);
        });
        bar.classList.add(`diff-bg-${next}`);
        btn.classList.add(`diff-text-${next}`);
        btn.textContent = next;
    }

    function renderSemesters() {
        boardContainer.innerHTML = '';
        for (let s = 1; s <= 4; s++) {
            const col = document.createElement('div');
            col.className = 'semester-col';
            col.innerHTML = `
                <div class="semester-header flex justify-between items-center">
                    <h3 class="text-lg font-bold text-white">Semester ${s}</h3>
                    <div class="ects-badge ects-normal" id="ects-sem-${s}">0 / 30 ECTS</div>
                </div>
                <div class="semester-body custom-scrollbar" id="sem-${s}" data-sem="${s}"></div>
            `;
            boardContainer.appendChild(col);

            const body = col.querySelector(`#sem-${s}`);
            boardState.semesters[s].forEach(id => {
                const card = createCard(id);
                if (card) body.appendChild(card);
            });
        }
    }

    const filtersContainer = document.getElementById('filtersContainer');

    const activeFilters = {
        pillar: new Set(),
        term: new Set(),
        status: new Set(),
        type: new Set(),
        ects: new Set(),
        difficulty: new Set()
    };

    function renderPool() {
        poolContainer.innerHTML = '';
        const termQ = searchInput.value.toLowerCase();

        boardState.pool.forEach(id => {
            const c = courseMap[id];
            if (!c) return;

            // Search text
            if (termQ && !c.name.toLowerCase().includes(termQ) && !c.id.includes(termQ)) return;

            // Pillar
            if (activeFilters.pillar.size > 0 && !activeFilters.pillar.has(c.pillar)) return;

            // Term (All current data is Summer 2026 based on FPO)
            const cTerm = "Summer";
            if (activeFilters.term.size > 0 && !activeFilters.term.has(cTerm)) return;

            // Status
            const cStatus = (c.examDate && c.professor !== 'N/A') ? "Presented" : "Not Presented";
            if (activeFilters.status.size > 0 && !activeFilters.status.has(cStatus)) return;

            // Type
            if (activeFilters.type.size > 0 && !activeFilters.type.has(c.type)) return;

            // ECTS
            if (activeFilters.ects.size > 0 && !activeFilters.ects.has(String(c.ects))) return;

            // Difficulty
            const cDiff = boardState.difficulties[id] || c.defaultDifficulty || 'Medium';
            if (activeFilters.difficulty.size > 0 && !activeFilters.difficulty.has(cDiff)) return;

            const card = createCard(id);
            if (card) poolContainer.appendChild(card);
        });
    }

    function updateCalculations() {
        // Update ECTS
        for (let s = 1; s <= 4; s++) {
            const ids = boardState.semesters[s];
            const totalEcts = ids.reduce((sum, id) => sum + (courseMap[id]?.ects || 0), 0);

            const badge = document.getElementById(`ects-sem-${s}`);
            badge.textContent = `${totalEcts} / 30 ECTS`;

            badge.className = 'ects-badge';
            if (totalEcts >= 30) badge.classList.add('ects-success');
            else badge.classList.add('ects-normal');
        }

        // Validate Exam Gaps (4 Days)
        document.querySelectorAll('.course-card').forEach(c => c.classList.remove('exam-collision', 'border-red-500'));

        for (let s = 1; s <= 4; s++) {
            const ids = boardState.semesters[s];
            const exams = [];
            ids.forEach(id => {
                const c = courseMap[id];
                if (c && c.examDate) {
                    exams.push({ id, date: new Date(c.examDate) });
                }
            });

            // Sort by date
            exams.sort((a, b) => a.date - b.date);

            for (let i = 0; i < exams.length - 1; i++) {
                const d1 = exams[i].date;
                const d2 = exams[i + 1].date;
                const diffTime = Math.abs(d2 - d1);
                const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

                if (diffDays < 4) {
                    // Collision
                    const card1 = document.querySelector(`.course-card[data-id="${exams[i].id}"]`);
                    const card2 = document.querySelector(`.course-card[data-id="${exams[i + 1].id}"]`);
                    if (card1) card1.classList.add('exam-collision');
                    if (card2) card2.classList.add('exam-collision');
                }
            }
        }
    }

    function saveState() {
        localStorage.setItem('uniplan_state', JSON.stringify(boardState));
        updateCalculations();
        if (typeof currentUser !== 'undefined' && currentUser) {
            syncToFirestore();
        }
    }

    // 4. Initialize SortableJS
    function initSortable() {
        const sharedConfig = {
            group: 'shared',
            animation: 150,
            ghostClass: 'sortable-ghost',
            dragClass: 'sortable-drag',
            onEnd: function (evt) {
                const id = evt.item.dataset.id;
                const fromList = evt.from.id;
                const toList = evt.to.id;

                if (fromList === toList) return; // Didn't change list

                // Remove from old
                if (fromList === 'poolContainer') {
                    boardState.pool = boardState.pool.filter(i => i !== id);
                } else {
                    const s = evt.from.dataset.sem;
                    boardState.semesters[s] = boardState.semesters[s].filter(i => i !== id);
                }

                // Add to new
                if (toList === 'poolContainer') {
                    boardState.pool.push(id);
                } else {
                    const s = evt.to.dataset.sem;
                    boardState.semesters[s].push(id);
                }

                saveState();
            }
        };

        new Sortable(poolContainer, sharedConfig);

        for (let s = 1; s <= 4; s++) {
            const body = document.getElementById(`sem-${s}`);
            new Sortable(body, sharedConfig);
        }
    }

    // 5. Modal Logic
    function showModal(id) {
        const c = courseMap[id];
        if (!c) return;

        modalId.textContent = c.id;
        modalTitle.textContent = c.name;
        modalEcts.textContent = c.ects;
        modalDate.textContent = c.examDate || 'TBA';
        modalProf.textContent = c.professor || 'N/A';
        modalPillar.textContent = `${c.pillar !== 'General' ? c.pillar : 'General Module'} • ${c.type}`;
        modalDesc.textContent = c.description || 'No description available.';

        modal.classList.remove('hidden');
        // small delay to allow display block to apply before animating opacity
        setTimeout(() => {
            modal.classList.remove('opacity-0');
            modal.querySelector('.modal-content').classList.remove('scale-95');
        }, 10);
    }

    function hideModal() {
        modal.classList.add('opacity-0');
        modal.querySelector('.modal-content').classList.add('scale-95');
        setTimeout(() => {
            modal.classList.add('hidden');
        }, 300);
    }

    closeModalBtn.addEventListener('click', hideModal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) hideModal();
    });

    // 6. Events
    searchInput.addEventListener('input', renderPool);

    // Dynamic Filter generation
    function createFilterGroup(title, key, options) {
        const group = document.createElement('div');
        group.className = 'filter-group flex flex-col gap-1';

        const header = document.createElement('div');
        header.className = 'text-[10px] font-bold text-gray-400 uppercase tracking-wider pl-1';
        header.textContent = title;
        group.appendChild(header);

        const pills = document.createElement('div');
        pills.className = 'flex flex-wrap gap-1.5';

        options.forEach(opt => {
            const btn = document.createElement('button');
            btn.className = 'filter-btn';
            btn.textContent = opt;
            btn.addEventListener('click', () => {
                if (activeFilters[key].has(opt)) {
                    activeFilters[key].delete(opt);
                    btn.classList.remove('active');
                } else {
                    activeFilters[key].add(opt);
                    btn.classList.add('active');
                }
                renderPool();
            });
            pills.appendChild(btn);
        });

        group.appendChild(pills);
        filtersContainer.appendChild(group);
    }

    const pillars = new Set();
    const ectsVals = new Set();
    COURSE_DATA.forEach(c => {
        if (c.pillar && c.pillar !== "General") pillars.add(c.pillar);
        if (c.ects) ectsVals.add(String(c.ects));
    });

    // We add "General" manually at the start
    const pillarArray = Array.from(pillars).sort();
    pillarArray.unshift("General");

    createFilterGroup('Pillar', 'pillar', pillarArray);
    createFilterGroup('Type', 'type', ['Core', 'Elective', 'Seminar']);
    createFilterGroup('Term', 'term', ['Summer', 'Winter']);
    createFilterGroup('Status', 'status', ['Presented', 'Not Presented']);
    createFilterGroup('ECTS', 'ects', Array.from(ectsVals).sort((a, b) => Number(a) - Number(b)));
    createFilterGroup('Difficulty', 'difficulty', ['Low', 'Medium', 'High']);

    resetBtn.addEventListener('click', () => {
        if (confirm("Are you sure you want to reset your entire plan?")) {
            localStorage.removeItem('uniplan_state');
            location.reload();
        }
    });

    // Sidebar Expand Logic
    const expandBtn = document.getElementById('expandBtn');
    const sidebar = document.getElementById('sidebar');
    let isSidebarExpanded = false;
    expandBtn.addEventListener('click', () => {
        isSidebarExpanded = !isSidebarExpanded;
        if (isSidebarExpanded) {
            sidebar.style.width = '600px';
        } else {
            sidebar.style.width = '350px';
        }
    });

    // --- FIREBASE CONFIGURATION (Update this with your own config) ---
    const firebaseConfig = {
        apiKey: "AIzaSyArvqHa0QsxFsL5al_p5ejxTrTWi1yvHXU",
        authDomain: "uniplan-d1c49.firebaseapp.com",
        projectId: "uniplan-d1c49",
        storageBucket: "uniplan-d1c49.firebasestorage.app",
        messagingSenderId: "148809029657",
        appId: "1:148809029657:web:44ecb73d415507737eb288",
        measurementId: "G-S5P6JX5QL7"
    };

    let app, auth, db;
    let currentUser = null;

    // Initialize Firebase only if the user replaces the dummy key
    if (firebaseConfig.apiKey !== "YOUR_API_KEY" && typeof firebase !== 'undefined') {
        app = firebase.initializeApp(firebaseConfig);
        auth = firebase.auth();
        db = firebase.firestore();

        auth.onAuthStateChanged(user => {
            currentUser = user;
            const openLoginBtn = document.getElementById('openLoginBtn');
            if (user) {
                openLoginBtn.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"></path></svg> Logout (${user.email})`;
                openLoginBtn.classList.replace('text-brand-500', 'text-red-400');
                openLoginBtn.classList.replace('hover:text-brand-400', 'hover:text-red-300');
                fetchFromFirestore();
            } else {
                openLoginBtn.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1"></path></svg> Login to Sync`;
                openLoginBtn.classList.replace('text-red-400', 'text-brand-500');
                openLoginBtn.classList.replace('hover:text-red-300', 'hover:text-brand-400');
            }
        });
    }

    async function syncToFirestore() {
        if (!currentUser || !db) return;
        try {
            await db.collection('users').doc(currentUser.uid).set({ plan: boardState });
        } catch (e) {
            console.error("Error syncing to Firestore:", e);
        }
    }

    async function fetchFromFirestore() {
        if (!currentUser || !db) return;
        try {
            const doc = await db.collection('users').doc(currentUser.uid).get();
            if (doc.exists && doc.data().plan) {
                boardState = doc.data().plan;
                renderSemesters();
                renderPool();
                updateCalculations();
            }
        } catch (e) {
            console.error("Error fetching from Firestore:", e);
        }
    }

    // Modal & Auth Logic
    const authModal = document.getElementById('authModal');
    const openLoginBtn = document.getElementById('openLoginBtn');
    const closeAuthModalBtn = document.getElementById('closeAuthModalBtn');
    const authForm = document.getElementById('authForm');
    const authError = document.getElementById('authError');

    if (openLoginBtn) {
        openLoginBtn.addEventListener('click', () => {
            if (currentUser) {
                auth.signOut();
            } else {
                if (firebaseConfig.apiKey === "YOUR_API_KEY") {
                    alert("Please configure Firebase in app.js first!");
                    return;
                }
                authError.classList.add('hidden');
                authModal.classList.remove('hidden');
                setTimeout(() => {
                    authModal.classList.remove('opacity-0');
                    authModal.querySelector('.modal-content').classList.remove('scale-95');
                }, 10);
            }
        });
    }

    if (closeAuthModalBtn) {
        closeAuthModalBtn.addEventListener('click', hideAuthModal);
    }

    function hideAuthModal() {
        authModal.classList.add('opacity-0');
        authModal.querySelector('.modal-content').classList.add('scale-95');
        setTimeout(() => authModal.classList.add('hidden'), 300);
    }

    if (authForm) {
        authForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('authEmail').value;
            const pass = document.getElementById('authPassword').value;

            try {
                // Try sign in
                await auth.signInWithEmailAndPassword(email, pass);
                hideAuthModal();
            } catch (error) {
                if (error.code === 'auth/user-not-found' || error.code === 'auth/invalid-credential') {
                    try {
                        // Auto-register if not found
                        await auth.createUserWithEmailAndPassword(email, pass);
                        hideAuthModal();
                    } catch (regError) {
                        authError.textContent = regError.message;
                        authError.classList.remove('hidden');
                    }
                } else {
                    authError.textContent = error.message;
                    authError.classList.remove('hidden');
                }
            }
        });
    }

    // 7. Initial Render
    renderSemesters();
    renderPool();
    initSortable();
    updateCalculations();
});
