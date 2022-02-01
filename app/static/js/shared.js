window.addEventListener('click', function (event) {
    // Modal
    var modal = document.getElementById('modal');
    var closeModal = [modal, document.getElementById('closeModal'),
        document.getElementById('cancelModal')]
    if (event.target.closest('#openModal')) {
        modal.style.display = 'flex'
    } else if (closeModal.includes(event.target)) {
        modal.style.display = "none";
    }

    // Dropdown menu
    var dropContent = document.querySelector('.dropdown-content');
    if (event.target.closest('.username')) {
        dropContent.classList.add('show-dropdown');
    } else if (!event.target.closest('.dropdown')) {
        dropContent.classList.remove('show-dropdown');
    }

    // Mobile search form
    var searchForm = document.querySelector('.search-form');
    if (event.target.closest('.search-button-mobile')) {
        searchForm.classList.remove('hide');
        searchForm.classList.add('search-form-mobile');
    } else if (!event.target.closest('.search-form')) {
        searchForm.classList.add('hide');
        searchForm.classList.remove('search-form-mobile');
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