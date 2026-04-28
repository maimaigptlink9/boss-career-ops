function app() {
    return {
        currentPage: 'dashboard',
        allJobs: [],
        recommendedJobs: [],
        filteredJobs: [],
        filterStage: '',
        selectedJob: null,
        stageCounts: {},
        profile: { name: '', title: '', expected_salary_min: '', expected_salary_max: '', preferred_cities_str: '', skills_str: '' },
        profileSaved: false,
        aiStatus: { configured: false, provider: '', source: 'none' },
        providers: [],
        aiProvider: 'deepseek',
        aiApiKey: '',
        aiConfigSaved: false,
        authStatus: { ok: false },
        aiTab: 'reply',
        aiJobId: '',
        aiMessage: '',
        aiSuggestions: [],
        stageOrder: ['discovered', 'evaluated', 'applied', 'chatting', 'interview'],
        stageLabels: { discovered: '发现', evaluated: '评估', applied: '投递', chatting: '沟通', interview: '面试' },
        scoreDimensions: ['匹配度', '薪资', '地点', '发展', '团队'],
        dimWeights: { '匹配度': 30, '薪资': 25, '地点': 15, '发展': 15, '团队': 15 },

        init() {
            this.navigate(location.hash || '#/dashboard');
            window.onhashchange = () => this.navigate(location.hash);
            this.loadStats();
            this.loadPipeline();
            this.loadProfile();
            this.loadAiStatus();
            this.loadProviders();
            this.loadAuthStatus();
        },

        navigate(hash) {
            if (!hash || hash === '#/') hash = '#/dashboard';
            location.hash = hash;
            this.currentPage = hash.replace('#/', '');
            if (this.currentPage === 'dashboard') {
                this.loadPipeline();
                this.loadStats();
            }
        },

        async loadPipeline(stage) {
            try {
                const url = stage ? `/api/pipeline?stage=${stage}` : '/api/pipeline';
                const res = await fetch(url);
                const data = await res.json();
                if (data.ok) {
                    this.allJobs = data.data || [];
                    this.recommendedJobs = this.allJobs.filter(j => j.grade === 'A' || j.grade === 'B').slice(0, 10);
                    this.applyFilter();
                }
            } catch (e) { console.error('loadPipeline:', e); }
        },

        async loadStats() {
            try {
                const res = await fetch('/api/stats');
                const data = await res.json();
                if (data.ok) {
                    this.stageCounts = data.data.by_stage || {};
                }
            } catch (e) { console.error('loadStats:', e); }
        },

        async loadProfile() {
            try {
                const res = await fetch('/api/profile');
                const data = await res.json();
                if (data.ok && data.data) {
                    const p = data.data;
                    this.profile.name = p.name || '';
                    this.profile.title = p.title || '';
                    this.profile.expected_salary_min = p.expected_salary?.min ? Math.round(p.expected_salary.min / 1000) : '';
                    this.profile.expected_salary_max = p.expected_salary?.max ? Math.round(p.expected_salary.max / 1000) : '';
                    this.profile.preferred_cities_str = (p.preferred_cities || []).join(', ');
                    this.profile.skills_str = (p.skills || []).join(', ');
                }
            } catch (e) { console.error('loadProfile:', e); }
        },

        async saveProfile() {
            try {
                const body = {
                    name: this.profile.name,
                    title: this.profile.title,
                    expected_salary: {
                        min: this.profile.expected_salary_min ? parseInt(this.profile.expected_salary_min) * 1000 : 0,
                        max: this.profile.expected_salary_max ? parseInt(this.profile.expected_salary_max) * 1000 : 0,
                    },
                    preferred_cities: this.profile.preferred_cities_str.split(/[,，]/).map(s => s.trim()).filter(Boolean),
                    skills: this.profile.skills_str.split(/[,，]/).map(s => s.trim()).filter(Boolean),
                };
                const res = await fetch('/api/profile', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
                const data = await res.json();
                if (data.ok) {
                    this.profileSaved = true;
                    setTimeout(() => { this.profileSaved = false; }, 2000);
                }
            } catch (e) { console.error('saveProfile:', e); }
        },

        async loadAiStatus() {
            try {
                const res = await fetch('/api/settings/ai');
                const data = await res.json();
                if (data.ok) this.aiStatus = data.data;
            } catch (e) { console.error('loadAiStatus:', e); }
        },

        async loadProviders() {
            try {
                const res = await fetch('/api/settings/providers');
                const data = await res.json();
                if (data.ok) {
                    this.providers = data.data || [];
                    if (this.providers.length && !this.aiProvider) {
                        this.aiProvider = this.providers[0].id;
                    }
                }
            } catch (e) { console.error('loadProviders:', e); }
        },

        get selectedProviderInfo() {
            return this.providers.find(p => p.id === this.aiProvider) || null;
        },

        async saveAiConfig() {
            try {
                const res = await fetch('/api/settings/ai', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ provider: this.aiProvider, api_key: this.aiApiKey }),
                });
                const data = await res.json();
                if (data.ok) {
                    this.aiConfigSaved = true;
                    this.aiStatus = data.data;
                    this.aiApiKey = '';
                    setTimeout(() => { this.aiConfigSaved = false; }, 2000);
                }
            } catch (e) { console.error('saveAiConfig:', e); }
        },

        async loadAuthStatus() {
            try {
                const res = await fetch('/api/auth/status');
                const data = await res.json();
                if (data.ok) this.authStatus = data.data;
            } catch (e) { console.error('loadAuthStatus:', e); }
        },

        async selectJob(jobId) {
            try {
                const res = await fetch(`/api/jobs/${jobId}`);
                const data = await res.json();
                if (data.ok) {
                    this.selectedJob = data.data;
                }
            } catch (e) { console.error('selectJob:', e); }
        },

        async greetRecruiter(job) {
            if (!job.security_id) { alert('该职位缺少 security_id，无法打招呼'); return; }
            if (!confirm(`确认向 ${job.company_name} · ${job.job_name} 打招呼？`)) return;
            try {
                const res = await fetch('/api/greet', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ security_id: job.security_id, job_id: job.job_id }),
                });
                const data = await res.json();
                if (data.ok) alert('打招呼成功');
                else alert('打招呼失败：' + data.error);
            } catch (e) { alert('打招呼失败：' + e.message); }
        },

        async getReplySuggest() {
            try {
                const res = await fetch('/api/ai/reply-suggest', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ security_id: '', job_id: this.aiJobId }),
                });
                const data = await res.json();
                if (data.ok) {
                    this.aiSuggestions = data.data.suggestions || [];
                    if (this.aiSuggestions.length === 0) {
                        this.aiSuggestions = ['暂无 AI 建议，请确保已配置 API Key 并选择有效职位'];
                    }
                } else if (data.code === 'AI_NOT_CONFIGURED') {
                    this.navigate('#/settings');
                } else {
                    alert('生成失败：' + data.error);
                }
            } catch (e) { alert('生成失败：' + e.message); }
        },

        setFilterStage(stage) {
            this.filterStage = stage;
            this.applyFilter();
        },

        applyFilter() {
            if (!this.filterStage) {
                this.filteredJobs = this.allJobs;
            } else {
                this.filteredJobs = this.allJobs.filter(j => j.stage === this.filterStage);
            }
        },

        scoreWidth(score) {
            return Math.max(0, Math.min(100, ((score || 0) / 5) * 100));
        },

        scoreBarClass(score) {
            if (score >= 3.5) return 'bar-high';
            if (score >= 2.5) return 'bar-mid';
            if (score >= 1.5) return 'bar-low';
            return 'bar-vlow';
        },

        copyText(text) {
            navigator.clipboard.writeText(text).then(() => {
                alert('已复制到剪贴板');
            }).catch(() => {
                const ta = document.createElement('textarea');
                ta.value = text;
                document.body.appendChild(ta);
                ta.select();
                document.execCommand('copy');
                document.body.removeChild(ta);
                alert('已复制到剪贴板');
            });
        },
    };
}
