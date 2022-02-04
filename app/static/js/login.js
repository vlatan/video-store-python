var needLogin = document.querySelector('.need-login');
var login = document.querySelectorAll('[data-auth]');

document.addEventListener('click', (event) => {
    if (Array.from(login).includes(event.target)) {
        needLogin.style.display = 'block';
    }

    else if (needLogin.style.display === 'block' && event.target != needLogin) {
        needLogin.removeAttribute('style');
    }
});