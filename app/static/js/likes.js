function setFaveStatus(action) {
    let text = 'Save';
    if (action === 'fave') {
        text = 'Saved';
    }
    document.querySelector('[data-status]').textContent = text;
}

function setLikeCounter(action) {
    let text = document.querySelector('[data-likes]').textContent.trim();
    let counter = parseInt(text.charAt(0));
    if (isNaN(counter)) {
        counter = 0;
    }
    if (action === 'like') {
        counter += 1;
    } else {
        counter -= 1;
    }
    if (counter === 0) {
        text = 'Like';
    } else if (counter === 1) {
        text = '1 Like';
    } else {
        text = `${counter} Likes`;
    }
    document.querySelector('[data-likes]').textContent = text;
}

async function performAction(action) {
    const url = `${window.location.pathname}${action}`;
    return await fetch(url, { method: 'POST' });
}

function listenForAction(event, action) {
    const actionElement = event.target.closest(`.${action}`);
    if (actionElement) {
        actionElement.classList.toggle(`${action}-no`);
        actionElement.classList.toggle(`${action}-yes`);
        let currentAction = action;
        if (actionElement.classList.contains(`${action}-no`)) {
            currentAction = `un${action}`;
        }
        performAction(currentAction)
            .then(response => {
                if (response.ok) {
                    var icon = actionElement.querySelector('.action-icon');
                    if (currentAction.includes('like')) {
                        setLikeCounter(currentAction);
                        if (currentAction === 'like') {
                            icon.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="white" d="M12 4.248c-3.148-5.402-12-3.825-12 2.944 0 4.661 5.571 9.427 12 15.808 6.43-6.381 12-11.147 12-15.808 0-6.792-8.875-8.306-12-2.944z" /></svg>';
                        } else {
                            icon.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="white" d="M6.28 3c3.236.001 4.973 3.491 5.72 5.031.75-1.547 2.469-5.021 5.726-5.021 2.058 0 4.274 1.309 4.274 4.182 0 3.442-4.744 7.851-10 13-5.258-5.151-10-9.559-10-13 0-2.676 1.965-4.193 4.28-4.192zm.001-2c-3.183 0-6.281 2.187-6.281 6.192 0 4.661 5.57 9.427 12 15.808 6.43-6.381 12-11.147 12-15.808 0-4.011-3.097-6.182-6.274-6.182-2.204 0-4.446 1.042-5.726 3.238-1.285-2.206-3.522-3.248-5.719-3.248z" /></svg>';
                        }
                    } else {
                        setFaveStatus(currentAction);
                        if (currentAction === 'fave') {
                            icon.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="white" d="M12 .587l3.668 7.568 8.332 1.151-6.064 5.828 1.48 8.279-7.416-3.967-7.417 3.967 1.481-8.279-6.064-5.828 8.332-1.151z" /></svg>';
                        } else {
                            icon.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="white" d="M12 5.173l2.335 4.817 5.305.732-3.861 3.71.942 5.27-4.721-2.524-4.721 2.525.942-5.27-3.861-3.71 5.305-.733 2.335-4.817zm0-4.586l-3.668 7.568-8.332 1.151 6.064 5.828-1.48 8.279 7.416-3.967 7.416 3.966-1.48-8.279 6.064-5.827-8.332-1.15-3.668-7.569z" /></svg>';
                        }
                    }
                }
            });
    }
}

document.addEventListener('click', (event) => {
    listenForAction(event, 'like');
    listenForAction(event, 'fave');
});