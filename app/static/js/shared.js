function useModal(event, openModalID, modal, closeModalElements) {
    if (event.target.closest(openModalID)) {
        modal.style.display = 'flex'
    } else if (closeModalElements.includes(event.target)) {
        modal.removeAttribute('style');
    }
}

window.addEventListener('click', function (event) {
    const modals = [
        ['#openLoginModal', 'loginModal', 'closeLoginModal', 'cancelLoginModal'],
        ['#openAccountModal', 'deleteAccountModal', 'closeAccountModal', 'cancelAccountModal'],
        ['#openVideoModal', 'deleteVideoModal', 'closeVideoModal', 'cancelVideoModal']
    ]

    for (var i = 0; i < 3; i++) {
        var modal = document.getElementById(modals[i][1]);
        var closeModal = document.getElementById(modals[i][2]);
        var cancelModal = document.getElementById(modals[i][3]);
        var closeModalElements = [modal, closeModal, cancelModal]
        useModal(event, modals[i][0], modal, closeModalElements);
    }

    // Dropdown menu
    var dropContent = document.querySelector('.dropdown-content');
    var isntDropped = !dropContent.classList.contains('show-dropdown');
    var usernameClicked = event.target.closest('.username');
    if (isntDropped && usernameClicked) {
        dropContent.classList.add('show-dropdown');
    } else if (!event.target.closest('.show-dropdown')) {
        dropContent.classList.remove('show-dropdown');
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
    var logIn = document.getElementById('logInMessage');
    logIn.classList.add('alert');
    if (loginState === 'bingo') {
        logIn.innerText = "You've been logged in!";
    } else if (loginState === 'bummer') {
        logIn.innerText = "Sorry, something went wrong!";
    }
}
// remove login state
localStorage.removeItem('LoggedIn');