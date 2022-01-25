
// modal
var openModal = document.getElementById('openModal');
var noModal = [document.getElementById('modal'),
document.getElementById('closeModal'),
document.getElementById('cancelModal')]

window.onclick = function (event) {
    if (event.target == openModal) {
        modal.style.display = 'flex'
    }
    else if (noModal.includes(event.target)) {
        modal.style.display = "none";
    }
}

// get login state
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