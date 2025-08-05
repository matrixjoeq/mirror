// 趋势交易跟踪系统 JavaScript

// 全局配置
const APP_CONFIG = {
    apiBase: '/api',
    dateFormat: 'YYYY-MM-DD',
    currencySymbol: '¥',
    decimalPlaces: {
        price: 3,
        percentage: 2
    }
};

// 工具函数
const Utils = {
    // 格式化数字
    formatNumber: function(num, decimals = 2) {
        if (num === null || num === undefined) return '0.00';
        return parseFloat(num).toFixed(decimals);
    },

    // 格式化货币
    formatCurrency: function(amount, decimals = 3) {
        if (amount === null || amount === undefined) return APP_CONFIG.currencySymbol + '0.000';
        return APP_CONFIG.currencySymbol + this.formatNumber(amount, decimals);
    },

    // 格式化百分比
    formatPercentage: function(value, decimals = 2) {
        if (value === null || value === undefined) return '0.00%';
        return this.formatNumber(value, decimals) + '%';
    },

    // 格式化带符号的数字
    formatSignedNumber: function(num, decimals = 3, isCurrency = false) {
        if (num === null || num === undefined) return '0.00';
        const formatted = this.formatNumber(Math.abs(num), decimals);
        const prefix = isCurrency ? APP_CONFIG.currencySymbol : '';
        
        if (num > 0) {
            return '+' + prefix + formatted;
        } else if (num < 0) {
            return prefix + '-' + formatted;
        } else {
            return prefix + formatted;
        }
    },

    // 获取数字的CSS类
    getNumberClass: function(num) {
        if (num > 0) return 'text-success fw-bold';
        if (num < 0) return 'text-danger fw-bold';
        return 'text-muted';
    },

    // 格式化日期
    formatDate: function(dateStr) {
        if (!dateStr) return '-';
        const date = new Date(dateStr);
        return date.toLocaleDateString('zh-CN');
    },

    // 计算日期差
    dateDiff: function(startDate, endDate) {
        const start = new Date(startDate);
        const end = endDate ? new Date(endDate) : new Date();
        const diffTime = Math.abs(end - start);
        return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    },

    // 显示提示消息
    showToast: function(message, type = 'info') {
        // 创建toast元素
        const toastHtml = `
            <div class="toast align-items-center text-white bg-${type} border-0" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="d-flex">
                    <div class="toast-body">
                        ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            </div>
        `;
        
        // 添加到页面
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            document.body.appendChild(toastContainer);
        }
        
        toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        
        // 显示toast
        const toastElement = toastContainer.lastElementChild;
        const toast = new bootstrap.Toast(toastElement);
        toast.show();
        
        // 自动移除
        toastElement.addEventListener('hidden.bs.toast', function() {
            toastElement.remove();
        });
    },

    // 确认对话框
    confirm: function(message, callback) {
        if (confirm(message)) {
            callback();
        }
    },

    // 防抖函数
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
};

// 数据管理
const DataManager = {
    // 缓存
    cache: new Map(),
    
    // 获取数据
    getData: function(endpoint, useCache = true) {
        if (useCache && this.cache.has(endpoint)) {
            return Promise.resolve(this.cache.get(endpoint));
        }
        
        return fetch(APP_CONFIG.apiBase + endpoint)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (useCache) {
                    this.cache.set(endpoint, data);
                }
                return data;
            })
            .catch(error => {
                console.error('Error fetching data:', error);
                throw error;
            });
    },

    // 发送数据
    postData: function(endpoint, data) {
        return fetch(APP_CONFIG.apiBase + endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .catch(error => {
            console.error('Error posting data:', error);
            throw error;
        });
    },

    // 清除缓存
    clearCache: function(endpoint = null) {
        if (endpoint) {
            this.cache.delete(endpoint);
        } else {
            this.cache.clear();
        }
    }
};

// 表格管理
const TableManager = {
    // 排序表格
    sortTable: function(table, columnIndex, ascending = true) {
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        
        rows.sort((a, b) => {
            const aValue = a.cells[columnIndex].textContent.trim();
            const bValue = b.cells[columnIndex].textContent.trim();
            
            // 尝试数字比较
            const aNum = parseFloat(aValue.replace(/[^0-9.-]/g, ''));
            const bNum = parseFloat(bValue.replace(/[^0-9.-]/g, ''));
            
            if (!isNaN(aNum) && !isNaN(bNum)) {
                return ascending ? aNum - bNum : bNum - aNum;
            }
            
            // 字符串比较
            return ascending ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue);
        });
        
        // 重新插入排序后的行
        rows.forEach(row => tbody.appendChild(row));
    },

    // 筛选表格
    filterTable: function(table, filterText, columnIndexes = null) {
        const tbody = table.querySelector('tbody');
        const rows = tbody.querySelectorAll('tr');
        
        rows.forEach(row => {
            const cells = columnIndexes ? 
                columnIndexes.map(i => row.cells[i]) : 
                Array.from(row.cells);
            
            const text = cells.map(cell => cell.textContent.toLowerCase()).join(' ');
            const shouldShow = text.includes(filterText.toLowerCase());
            
            row.style.display = shouldShow ? '' : 'none';
        });
    },

    // 高亮表格行
    highlightRow: function(row, duration = 3000) {
        row.classList.add('table-warning');
        setTimeout(() => {
            row.classList.remove('table-warning');
        }, duration);
    }
};

// 图表管理
const ChartManager = {
    charts: new Map(),
    
    // 创建图表
    createChart: function(canvasId, config) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;
        
        const chart = new Chart(ctx, config);
        this.charts.set(canvasId, chart);
        return chart;
    },

    // 更新图表数据
    updateChart: function(canvasId, data) {
        const chart = this.charts.get(canvasId);
        if (chart) {
            chart.data = data;
            chart.update();
        }
    },

    // 销毁图表
    destroyChart: function(canvasId) {
        const chart = this.charts.get(canvasId);
        if (chart) {
            chart.destroy();
            this.charts.delete(canvasId);
        }
    },

    // 默认图表配置
    getDefaultConfig: function(type = 'line') {
        const configs = {
            line: {
                type: 'line',
                options: {
                    responsive: true,
                    interaction: {
                        intersect: false,
                    },
                    scales: {
                        x: {
                            display: true,
                            title: {
                                display: true
                            }
                        },
                        y: {
                            display: true,
                            title: {
                                display: true
                            }
                        }
                    }
                }
            },
            doughnut: {
                type: 'doughnut',
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'bottom',
                        }
                    }
                }
            },
            bar: {
                type: 'bar',
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            }
        };
        
        return configs[type] || configs.line;
    }
};

// 表单验证
const FormValidator = {
    // 验证规则
    rules: {
        required: function(value) {
            return value !== null && value !== undefined && value.toString().trim() !== '';
        },
        
        number: function(value) {
            return !isNaN(parseFloat(value)) && isFinite(value);
        },
        
        positive: function(value) {
            return this.number(value) && parseFloat(value) > 0;
        },
        
        integer: function(value) {
            return this.number(value) && Number.isInteger(parseFloat(value));
        },
        
        date: function(value) {
            return !isNaN(Date.parse(value));
        },
        
        min: function(value, min) {
            return this.number(value) && parseFloat(value) >= min;
        },
        
        max: function(value, max) {
            return this.number(value) && parseFloat(value) <= max;
        }
    },

    // 验证字段
    validateField: function(field, rules) {
        const value = field.value;
        const errors = [];
        
        for (const rule of rules) {
            const [ruleName, ...params] = rule.split(':');
            
            if (this.rules[ruleName]) {
                if (!this.rules[ruleName](value, ...params)) {
                    errors.push(this.getErrorMessage(ruleName, params));
                }
            }
        }
        
        return errors;
    },

    // 获取错误消息
    getErrorMessage: function(ruleName, params) {
        const messages = {
            required: '此字段为必填项',
            number: '请输入有效数字',
            positive: '请输入正数',
            integer: '请输入整数',
            date: '请输入有效日期',
            min: `值不能小于 ${params[0]}`,
            max: `值不能大于 ${params[0]}`
        };
        
        return messages[ruleName] || '输入无效';
    },

    // 验证表单
    validateForm: function(form, validationRules) {
        const errors = {};
        let isValid = true;
        
        for (const [fieldName, rules] of Object.entries(validationRules)) {
            const field = form.querySelector(`[name="${fieldName}"]`);
            if (field) {
                const fieldErrors = this.validateField(field, rules);
                if (fieldErrors.length > 0) {
                    errors[fieldName] = fieldErrors;
                    isValid = false;
                }
            }
        }
        
        return { isValid, errors };
    }
};

// 页面初始化
document.addEventListener('DOMContentLoaded', function() {
    // 初始化工具提示
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // 初始化弹出框
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // 自动关闭警告框
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, 5000);
    });

    // 表格排序功能
    const sortableTables = document.querySelectorAll('.table-sortable');
    sortableTables.forEach(table => {
        const headers = table.querySelectorAll('th[data-sort]');
        headers.forEach(header => {
            header.style.cursor = 'pointer';
            header.addEventListener('click', function() {
                const columnIndex = this.cellIndex;
                const isAscending = !this.classList.contains('sort-asc');
                
                // 移除其他列的排序标识
                headers.forEach(h => h.classList.remove('sort-asc', 'sort-desc'));
                
                // 添加当前列的排序标识
                this.classList.add(isAscending ? 'sort-asc' : 'sort-desc');
                
                // 排序表格
                TableManager.sortTable(table, columnIndex, isAscending);
            });
        });
    });

    // 搜索功能
    const searchInputs = document.querySelectorAll('.table-search');
    searchInputs.forEach(input => {
        const tableId = input.dataset.table;
        const table = document.getElementById(tableId);
        
        if (table) {
            input.addEventListener('input', Utils.debounce(function() {
                TableManager.filterTable(table, this.value);
            }, 300));
        }
    });

    // 数字输入格式化
    const numberInputs = document.querySelectorAll('input[type="number"]');
    numberInputs.forEach(input => {
        input.addEventListener('blur', function() {
            if (this.value && !isNaN(this.value)) {
                const decimals = this.step ? this.step.split('.')[1]?.length || 0 : 0;
                this.value = parseFloat(this.value).toFixed(decimals);
            }
        });
    });

    // 自动保存表单
    const autoSaveForms = document.querySelectorAll('.auto-save');
    autoSaveForms.forEach(form => {
        const inputs = form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.addEventListener('change', Utils.debounce(function() {
                const formData = new FormData(form);
                const data = Object.fromEntries(formData.entries());
                
                // 保存到本地存储
                localStorage.setItem(`form_${form.id}`, JSON.stringify(data));
                Utils.showToast('表单已自动保存', 'success');
            }, 1000));
        });
        
        // 恢复表单数据
        const savedData = localStorage.getItem(`form_${form.id}`);
        if (savedData) {
            const data = JSON.parse(savedData);
            for (const [key, value] of Object.entries(data)) {
                const field = form.querySelector(`[name="${key}"]`);
                if (field) {
                    field.value = value;
                }
            }
        }
    });

    console.log('趋势交易跟踪系统已加载完成');
});

// 导出到全局
window.Utils = Utils;
window.DataManager = DataManager;
window.TableManager = TableManager;
window.ChartManager = ChartManager;
window.FormValidator = FormValidator;