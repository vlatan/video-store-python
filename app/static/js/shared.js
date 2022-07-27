// sleep time expects milliseconds
function sleep(time) {
    return new Promise((resolve) => setTimeout(resolve, time));
}

// Send/recieve data to/from backend
async function postData(url = '', data = {}) {
    const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    return response;
}

// Set alert message
function setAlert(message) {
    var alert = document.createElement('div');
    alert.classList.add('alert');
    alert.innerText = message;
    document.getElementById('footer').prepend(alert);
    sleep(2000).then(() => {
        alert.remove();
    });
}

document.addEventListener('click', function (event) {

    // Modals
    document.querySelectorAll('[data-modal]').forEach(function (element) {
        var modalName = element.dataset.modal;
        var modalBody = document.querySelector(`[data-body="${modalName}"]`);
        var closeModal = event.target.closest(`[data-close="${modalName}"]`);
        if (event.target.closest(`[data-modal="${modalName}"]`)) {
            modalBody.style.display = 'flex';
        } else if (event.target === modalBody || closeModal) {
            modalBody.removeAttribute('style');
        }
    });

    // Dropdown menu
    var dropContent = document.querySelector('.dropdown-content');
    if (dropContent) {
        var notDropped = !dropContent.classList.contains('show-dropdown');
        var usernameClicked = event.target.closest('.username');
        var deleteAccountClicked = event.target.closest('.delete-account');
        var menuNotClicked = !event.target.closest('.show-dropdown');
        if (notDropped && usernameClicked) {
            dropContent.classList.add('show-dropdown');
        } else if (deleteAccountClicked || menuNotClicked) {
            dropContent.classList.remove('show-dropdown');
        }
    }

    // Mobile search form
    var searchForm = document.getElementById('searchForm');
    var logo = document.querySelector('a.logo');
    var arrow = document.querySelector('button.search-arrow')
    var arrowClicked = event.target.closest('button.search-arrow');
    var outsideFormClicked = !event.target.closest('#searchForm');
    if (event.target.closest('.search-button-mobile')) {
        searchForm.style.display = 'flex'
        logo.style.display = "none";
        arrow.style.display = "block";
    } else if (arrowClicked || outsideFormClicked) {
        searchForm.removeAttribute('style');
        logo.removeAttribute('style');
        arrow.removeAttribute('style');
    }
});

// save login state for parent window
var loginState = localStorage.getItem('LoggedIn');
if (loginState) {
    if (loginState === 'true') {
        setAlert("You've been logged in!");
    } else if (loginState === 'false') {
        setAlert("Sorry, something went wrong!");
    }
    // remove login state
    localStorage.removeItem('LoggedIn');
}


// Cookies disclaimer
var acceptCookies = localStorage.getItem('acceptCookies');
var privacyPath = "/page/privacy/";
var currentPath = window.location.pathname;
if (currentPath !== privacyPath && acceptCookies !== 'true') {
    var snackbar = document.createElement('div');
    snackbar.classList.add('snackbar');
    document.getElementById('footer').after(snackbar);

    var snackbarLabel = document.createElement('div');
    snackbarLabel.classList.add('snackbar-label');
    snackbarLabel.innerText = "We serve cookies on this site to analyze traffic, \
    remember your preferences, and optimize your experience.";
    snackbar.appendChild(snackbarLabel);

    var snackbarActions = document.createElement('div');
    snackbarActions.classList.add('snackbar-actions');
    snackbar.appendChild(snackbarActions);

    var detailsLink = document.createElement('a');
    detailsLink.classList.add('cookies-button');
    detailsLink.href = privacyPath;
    detailsLink.target = '_blank';
    detailsLink.innerText = "More details";
    snackbarActions.appendChild(detailsLink);

    var buttonOK = document.createElement('button');
    buttonOK.classList.add('cookies-button');
    buttonOK.innerText = "OK";
    snackbarActions.appendChild(buttonOK);

    buttonOK.addEventListener('click', () => {
        localStorage.setItem('acceptCookies', true);
        snackbar.remove();
    });
}