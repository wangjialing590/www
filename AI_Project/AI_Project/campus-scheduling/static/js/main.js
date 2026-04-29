function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} position-fixed top-0 end-0 m-3`;
    notification.style.zIndex = '9999';
    notification.innerHTML = message;
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 3000);
}

function formatTime(date) {
    return date.toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

function debounce(func, wait) {
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

function validateExcelFile(file) {
    if (!file) {
        return { valid: false, message: '请选择文件' };
    }

    if (!file.name.endsWith('.xlsx')) {
        return { valid: false, message: '请上传xlsx格式的文件' };
    }

    const maxSize = 16 * 1024 * 1024;
    if (file.size > maxSize) {
        return { valid: false, message: '文件大小不能超过16MB' };
    }

    return { valid: true };
}

const API_BASE_URL = '';

async function fetchWithError(url, options = {}) {
    try {
        const response = await fetch(url, options);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.message || '请求失败');
        }

        return data;
    } catch (error) {
        if (error.message) {
            throw error;
        }
        throw new Error('网络错误，请稍后重试');
    }
}

function updateUIState(state) {
    const elements = {
        uploadBtn: document.getElementById('btn-upload'),
        startBtn: document.getElementById('btn-start'),
        stopBtn: document.getElementById('btn-stop'),
        exportBtn: document.getElementById('btn-export')
    };

    Object.keys(elements).forEach(key => {
        if (elements[key]) {
            elements[key].disabled = state[key] !== undefined ? !state[key] : false;
        }
    });
}

function setCookie(name, value, days = 1) {
    const expires = new Date();
    expires.setTime(expires.getTime() + days * 24 * 60 * 60 * 1000);
    document.cookie = name + '=' + value + ';expires=' + expires.toUTCString();
}

function getCookie(name) {
    const nameEQ = name + '=';
    const ca = document.cookie.split(';');
    for (let i = 0; i < ca.length; i++) {
        let c = ca[i];
        while (c.charAt(0) === ' ') c = c.substring(1, c.length);
        if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
    }
    return null;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        showNotification,
        formatTime,
        debounce,
        validateExcelFile,
        fetchWithError,
        updateUIState
    };
}