function app() {
    return {
        currentPage: 'dashboard',
        allJobs: [],
        recommendedJobs: [],
        filteredJobs: [],
        filterStage: '',
        filterStatus: 'active',
        selectedJob: null,
        selectedJobIds: new Set(),
        stageCounts: {},
        profile: { name: '', title: '', expected_salary_min: '', expected_salary_max: '', preferred_cities_str: '', skills_str: '', experience_years: '', remote_ok: false, education: '', career_goals: '', avoid: '' },
        profileSaved: false,
        aiStatus: { configured: false, provider: '', base_url: '', model: '', source: 'none' },
        providers: [],
        aiProvider: 'deepseek',
        aiApiKey: '',
        aiBaseUrl: '',
        aiModel: '',
        aiConfigSaved: false,
        authStatus: { ok: false },
        aiTab: 'reply',
        aiJobId: '',
        aiMessage: '',
        aiSuggestions: [],
        searchKeyword: '',
        searchCity: '',
        searchResults: [],
        searchLoading: false,
        searchSelectedIds: new Set(),
        evaluateLoading: false,
        chatContacts: [],
        chatMessages: [],
        chatSecurityId: '',
        chatLoading: false,
        chatMessage: '',
        chatSuggestions: [],
        chatSuggestionLoading: false,
        resumeContent: '',
        resumeLoading: false,
        interviewPrep: null,
        interviewLoading: false,
        analyticsData: null,
        salaryDistribution: {},
        gradeDistribution: {},
        stageFunnel: {},
        toasts: [],
        confirmDialog: { show: false, title: '', message: '', onConfirm: null },
        stageOrder: ['discovered', 'evaluated', 'applied', 'chatting', 'interview'],
        stageLabels: { discovered: '发现', evaluated: '评估', applied: '投递', chatting: '沟通', interview: '面试' },
        statusLabels: { active: '活跃', dismissed: '已排除' },
        scoreDimensions: ['匹配度', '薪资', '地点', '发展', '团队'],
        dimWeights: { '匹配度': 30, '薪资': 25, '地点': 15, '发展': 15, '团队': 15 },

        get totalJobs() {
            return this.allJobs.length;
        },

        get salaryMaxCount() {
            return Math.max(...Object.values(this.salaryDistribution), 1);
        },

        get funnelMaxCount() {
            return Math.max(...Object.values(this.stageFunnel), 1);
        },

        init() {
            this.navigate(location.hash || '#/dashboard');
            window.onhashchange = () => this.navigate(location.hash);
            this.loadStats();
            this.loadPipeline();
            this.loadProfile();
            this.loadAiStatus();
            this.loadProviders();
            this.loadAuthStatus();
            document.addEventListener('keydown', (e) => this.handleKeydown(e));
        },

        navigate(hash) {
            if (!hash || hash === '#/') hash = '#/dashboard';
            location.hash = hash;
            this.currentPage = hash.replace('#/', '');
            if (this.currentPage === 'dashboard') {
                this.loadPipeline();
                this.loadStats();
            }
            if (this.currentPage === 'chat') {
                this.loadChatList();
            }
            if (this.currentPage === 'analytics') {
                this.loadAnalytics();
            }
        },

        handleKeydown(e) {
            if (e.key === 'Escape') {
                if (this.confirmDialog.show) {
                    this.cancelConfirm();
                } else if (this.selectedJob) {
                    this.selectedJob = null;
                }
                return;
            }
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                this.navigate('#/search');
                setTimeout(() => {
                    const input = document.querySelector('.search-input');
                    if (input) input.focus();
                }, 100);
                return;
            }
            if (this.currentPage === 'dashboard' && !this.selectedJob) {
                if (e.key === 'j' || e.key === 'k') {
                    e.preventDefault();
                    const jobs = this.filteredJobs;
                    if (!jobs.length) return;
                    if (!this._focusedIndex) this._focusedIndex = -1;
                    if (e.key === 'j') this._focusedIndex = Math.min(this._focusedIndex + 1, jobs.length - 1);
                    if (e.key === 'k') this._focusedIndex = Math.max(this._focusedIndex - 1, 0);
                    this.selectJob(jobs[this._focusedIndex].job_id);
                    return;
                }
                if (e.key === 'Enter' && this._focusedIndex >= 0) {
                    const jobs = this.filteredJobs;
                    if (jobs[this._focusedIndex]) {
                        this.selectJob(jobs[this._focusedIndex].job_id);
                    }
                }
            }
        },

        async loadPipeline(stage, status) {
            try {
                const params = new URLSearchParams();
                if (stage) params.set('stage', stage);
                const s = status || this.filterStatus;
                if (s && s !== 'all') params.set('status', s);
                const url = '/api/pipeline' + (params.toString() ? '?' + params.toString() : '');
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
                    this.profile.experience_years = p.experience_years || '';
                    this.profile.remote_ok = p.remote_ok || false;
                    this.profile.education = p.education || '';
                    this.profile.career_goals = p.career_goals || '';
                    this.profile.avoid = p.avoid || '';
                }
            } catch (e) { console.error('loadProfile:', e); }
        },

        async saveProfile() {
            try {
                const body = {
                    name: this.profile.name,
                    title: this.profile.title,
                    expected_salary: {
                        min: this.profile.expected_salary_min ? parseInt(this.profile.expected_salary_min) * 1000 : null,
                        max: this.profile.expected_salary_max ? parseInt(this.profile.expected_salary_max) * 1000 : null,
                    },
                    preferred_cities: this.profile.preferred_cities_str.split(/[,，]/).map(s => s.trim()).filter(Boolean),
                    skills: this.profile.skills_str.split(/[,，]/).map(s => s.trim()).filter(Boolean),
                    experience_years: this.profile.experience_years ? parseInt(this.profile.experience_years) : 0,
                    remote_ok: this.profile.remote_ok,
                    education: this.profile.education,
                    career_goals: this.profile.career_goals,
                    avoid: this.profile.avoid,
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
                if (data.ok) {
                    this.aiStatus = data.data;
                    this.aiProvider = data.data.provider || 'deepseek';
                    this.aiBaseUrl = data.data.base_url || '';
                    this.aiModel = data.data.model || '';
                }
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

        onProviderChange() {
            const info = this.selectedProviderInfo;
            if (info) {
                this.aiBaseUrl = info.base_url || '';
                this.aiModel = info.default_model || '';
            }
        },

        async saveAiConfig() {
            try {
                const res = await fetch('/api/settings/ai', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ provider: this.aiProvider, api_key: this.aiApiKey, base_url: this.aiBaseUrl, model: this.aiModel }),
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
            if (this.selectedJob && this.selectedJob.job_id === jobId) {
                this.selectedJob = null;
                return;
            }
            try {
                const res = await fetch(`/api/jobs/${jobId}`);
                const data = await res.json();
                if (data.ok) {
                    this.selectedJob = data.data;
                }
            } catch (e) { console.error('selectJob:', e); }
        },

        async greetRecruiter(job) {
            if (!job.security_id) { this.showToast('该职位缺少 security_id，无法打招呼', 'warning'); return; }
            this.showConfirm('打招呼确认', `确认向 ${job.company_name} · ${job.job_name} 打招呼？`, async () => {
                try {
                    const res = await fetch('/api/greet', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ security_id: job.security_id, job_id: job.job_id }),
                    });
                    const data = await res.json();
                    if (data.ok) this.showToast('打招呼成功', 'success');
                    else this.showToast('打招呼失败：' + data.error, 'error');
                } catch (e) { this.showToast('打招呼失败：' + e.message, 'error'); }
            });
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
                    this.showToast('生成失败：' + data.error, 'error');
                }
            } catch (e) { this.showToast('生成失败：' + e.message, 'error'); }
        },

        setFilterStage(stage) {
            this.filterStage = stage;
            this.applyFilter();
        },

        setFilterStatus(status) {
            this.filterStatus = status;
            this.selectedJobIds.clear();
            this.loadPipeline(this.filterStage, status);
        },

        applyFilter() {
            if (!this.filterStage) {
                this.filteredJobs = this.allJobs;
            } else {
                this.filteredJobs = this.allJobs.filter(j => j.stage === this.filterStage);
            }
        },

        toggleJobSelect(jobId) {
            if (this.selectedJobIds.has(jobId)) {
                this.selectedJobIds.delete(jobId);
            } else {
                this.selectedJobIds.add(jobId);
            }
        },

        isJobSelected(jobId) {
            return this.selectedJobIds.has(jobId);
        },

        selectAllVisible() {
            if (this.selectedJobIds.size === this.filteredJobs.length) {
                this.selectedJobIds.clear();
            } else {
                this.selectedJobIds = new Set(this.filteredJobs.map(j => j.job_id));
            }
        },

        async dismissSelected() {
            const ids = [...this.selectedJobIds];
            if (!ids.length) { this.showToast('请先选择要排除的职位', 'warning'); return; }
            this.showConfirm('排除确认', `确认排除 ${ids.length} 个职位？`, async () => {
                try {
                    const res = await fetch('/api/pipeline/dismiss', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ job_ids: ids }),
                    });
                    const data = await res.json();
                    if (data.ok) {
                        this.showToast(`已排除 ${data.data.dismissed} 个职位`, 'success');
                        this.selectedJobIds.clear();
                        this.loadPipeline();
                        this.loadStats();
                    } else {
                        this.showToast('操作失败：' + data.error, 'error');
                    }
                } catch (e) { this.showToast('操作失败：' + e.message, 'error'); }
            });
        },

        async dismissSingle(jobId) {
            this.showConfirm('排除确认', '确认排除该职位？', async () => {
                try {
                    const res = await fetch('/api/pipeline/dismiss', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ job_ids: [jobId] }),
                    });
                    const data = await res.json();
                    if (data.ok) {
                        this.loadPipeline();
                        this.loadStats();
                    } else {
                        this.showToast('操作失败：' + data.error, 'error');
                    }
                } catch (e) { this.showToast('操作失败：' + e.message, 'error'); }
            });
        },

        async restoreSingle(jobId) {
            try {
                const res = await fetch('/api/pipeline/restore', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ job_id: jobId }),
                });
                const data = await res.json();
                if (data.ok) {
                    this.loadPipeline();
                    this.loadStats();
                } else {
                    this.showToast('恢复失败：' + data.error, 'error');
                }
            } catch (e) { this.showToast('恢复失败：' + e.message, 'error'); }
        },

        isUnevaluated(job) {
            return job.stage === '发现' && (!job.grade || job.grade === '');
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
                this.showToast('已复制到剪贴板', 'success');
            }).catch(() => {
                const ta = document.createElement('textarea');
                ta.value = text;
                document.body.appendChild(ta);
                ta.select();
                document.execCommand('copy');
                document.body.removeChild(ta);
                this.showToast('已复制到剪贴板', 'success');
            });
        },

        showToast(message, type = 'info') {
            const id = Date.now();
            this.toasts.push({ id, message, type });
            setTimeout(() => { this.toasts = this.toasts.filter(t => t.id !== id); }, 3000);
        },

        showConfirm(title, message, onConfirm) {
            this.confirmDialog = { show: true, title, message, onConfirm };
        },

        confirmAction() {
            if (this.confirmDialog.onConfirm) this.confirmDialog.onConfirm();
            this.confirmDialog.show = false;
        },

        cancelConfirm() {
            this.confirmDialog.show = false;
        },

        async searchJobs() {
            if (!this.searchKeyword.trim()) { this.showToast('请输入搜索关键词', 'warning'); return; }
            this.searchLoading = true;
            this.searchSelectedIds.clear();
            try {
                const res = await fetch('/api/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ keyword: this.searchKeyword, city: this.searchCity }),
                });
                const data = await res.json();
                if (data.ok) {
                    this.searchResults = data.data || [];
                    this.showToast(`找到 ${this.searchResults.length} 个职位`, 'success');
                } else {
                    this.showToast('搜索失败：' + data.error, 'error');
                }
            } catch (e) { this.showToast('搜索失败：' + e.message, 'error'); }
            finally { this.searchLoading = false; }
        },

        searchToggleSelect(jobId) {
            if (this.searchSelectedIds.has(jobId)) this.searchSelectedIds.delete(jobId);
            else this.searchSelectedIds.add(jobId);
        },

        searchSelectAll() {
            if (this.searchSelectedIds.size === this.searchResults.length) this.searchSelectedIds.clear();
            else this.searchSelectedIds = new Set(this.searchResults.map(j => j.job_id));
        },

        async searchBatchGreet() {
            const ids = [...this.searchSelectedIds];
            if (!ids.length) { this.showToast('请先选择职位', 'warning'); return; }
            this.showConfirm('批量打招呼', `确认向 ${ids.length} 个职位打招呼？`, async () => {
                let success = 0, fail = 0;
                for (const jobId of ids) {
                    const job = this.searchResults.find(j => j.job_id === jobId);
                    if (job && job.security_id) {
                        try {
                            const res = await fetch('/api/greet', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ security_id: job.security_id, job_id: job.job_id }),
                            });
                            const data = await res.json();
                            if (data.ok) success++; else fail++;
                        } catch (e) { fail++; }
                    } else { fail++; }
                }
                this.showToast(`打招呼完成：成功 ${success}，失败 ${fail}`, success > 0 ? 'success' : 'error');
                this.searchSelectedIds.clear();
            });
        },

        async applyJob(job) {
            if (!job.security_id) { this.showToast('该职位缺少 security_id，无法投递', 'warning'); return; }
            this.showConfirm('投递确认', `确认投递 ${job.company_name} · ${job.job_name}？投递操作不可撤回。`, async () => {
                try {
                    const res = await fetch('/api/apply', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ security_id: job.security_id, job_id: job.job_id }),
                    });
                    const data = await res.json();
                    if (data.ok) {
                        this.showToast('投递成功', 'success');
                        this.loadPipeline();
                        this.loadStats();
                    } else {
                        this.showToast('投递失败：' + data.error, 'error');
                    }
                } catch (e) { this.showToast('投递失败：' + e.message, 'error'); }
            });
        },

        async evaluateJob(jobId) {
            this.evaluateLoading = true;
            try {
                const res = await fetch('/api/evaluate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ job_id: jobId }),
                });
                const data = await res.json();
                if (data.ok) {
                    this.showToast('评估完成：' + (data.data.grade || ''), 'success');
                    if (this.selectedJob && this.selectedJob.job_id === jobId) {
                        this.selectedJob = await this.selectJob(jobId) || this.selectedJob;
                    }
                    this.loadPipeline();
                    this.loadStats();
                } else {
                    this.showToast('评估失败：' + data.error, 'error');
                }
            } catch (e) { this.showToast('评估失败：' + e.message, 'error'); }
            finally { this.evaluateLoading = false; }
        },

        async evaluatePending() {
            this.evaluateLoading = true;
            try {
                const res = await fetch('/api/evaluate/pending', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ limit: 50 }),
                });
                const data = await res.json();
                if (data.ok) {
                    this.showToast(`批量评估完成：${data.data.evaluated}/${data.data.total}`, 'success');
                    this.loadPipeline();
                    this.loadStats();
                } else {
                    this.showToast('批量评估失败：' + data.error, 'error');
                }
            } catch (e) { this.showToast('批量评估失败：' + e.message, 'error'); }
            finally { this.evaluateLoading = false; }
        },

        async loadAnalytics() {
            try {
                const [overviewRes, salaryRes, gradeRes, funnelRes] = await Promise.all([
                    fetch('/api/analytics/overview'),
                    fetch('/api/analytics/salary-distribution'),
                    fetch('/api/analytics/grade-distribution'),
                    fetch('/api/analytics/stage-funnel'),
                ]);
                const overview = await overviewRes.json();
                const salary = await salaryRes.json();
                const grade = await gradeRes.json();
                const funnel = await funnelRes.json();
                if (overview.ok) this.analyticsData = overview.data;
                if (salary.ok) this.salaryDistribution = salary.data;
                if (grade.ok) this.gradeDistribution = grade.data;
                if (funnel.ok) this.stageFunnel = funnel.data;
            } catch (e) { this.showToast('加载数据分析失败', 'error'); }
        },

        async loadChatList() {
            try {
                const res = await fetch('/api/chat-list');
                const data = await res.json();
                if (data.ok) {
                    this.chatContacts = data.data || [];
                }
            } catch (e) { this.showToast('获取聊天列表失败', 'error'); }
        },

        async loadChatMessages(securityId) {
            this.chatSecurityId = securityId;
            this.chatLoading = true;
            this.chatMessages = [];
            this.chatSuggestions = [];
            try {
                const res = await fetch(`/api/chat/${securityId}`);
                const data = await res.json();
                if (data.ok) {
                    this.chatMessages = data.data || [];
                }
            } catch (e) { this.showToast('获取聊天记录失败', 'error'); }
            finally { this.chatLoading = false; }
        },

        async generateResume(jobId) {
            if (!jobId) { this.showToast('请先选择职位', 'warning'); return; }
            this.resumeLoading = true;
            this.resumeContent = '';
            try {
                const res = await fetch('/api/resume/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ job_id: jobId }),
                });
                const data = await res.json();
                if (data.ok) {
                    this.resumeContent = data.data.content;
                    this.showToast('简历生成成功', 'success');
                } else {
                    this.showToast('简历生成失败：' + data.error, 'error');
                }
            } catch (e) { this.showToast('简历生成失败', 'error'); }
            finally { this.resumeLoading = false; }
        },

        async downloadResumePdf(jobId) {
            if (!jobId) { this.showToast('请先选择职位', 'warning'); return; }
            try {
                const res = await fetch(`/api/resume/${jobId}/pdf`);
                if (res.ok) {
                    const blob = await res.blob();
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `resume_${jobId}.pdf`;
                    a.click();
                    URL.revokeObjectURL(url);
                } else {
                    const data = await res.json();
                    this.showToast('PDF 下载失败：' + (data.error || '未知错误'), 'error');
                }
            } catch (e) { this.showToast('PDF 下载失败', 'error'); }
        },

        async prepareInterview(jobId) {
            if (!jobId) { this.showToast('请先选择职位', 'warning'); return; }
            this.interviewLoading = true;
            this.interviewPrep = null;
            try {
                const res = await fetch('/api/interview/prepare', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ job_id: jobId }),
                });
                const data = await res.json();
                if (data.ok) {
                    this.interviewPrep = data.data;
                    this.showToast('面试准备生成成功', 'success');
                } else {
                    this.showToast('面试准备失败：' + data.error, 'error');
                }
            } catch (e) { this.showToast('面试准备失败', 'error'); }
            finally { this.interviewLoading = false; }
        },

        async sendReplySuggest() {
            if (!this.chatSecurityId) { this.showToast('请先选择联系人', 'warning'); return; }
            this.chatSuggestionLoading = true;
            this.chatSuggestions = [];
            try {
                const res = await fetch('/api/ai/reply-suggest', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ security_id: this.chatSecurityId, message: this.chatMessage }),
                });
                const data = await res.json();
                if (data.ok) {
                    this.chatSuggestions = data.data.suggestions || [];
                    if (this.chatSuggestions.length === 0) {
                        this.chatSuggestions = ['暂无 AI 建议'];
                    }
                } else if (data.code === 'AI_NOT_CONFIGURED') {
                    this.showToast('AI 未配置，请先设置 API Key', 'warning');
                    this.navigate('#/settings');
                } else {
                    this.showToast('生成建议失败：' + data.error, 'error');
                }
            } catch (e) { this.showToast('生成建议失败', 'error'); }
            finally { this.chatSuggestionLoading = false; }
        },
    };
}
