function setFaveStatus(action) {
    let text = 'Save';
    if (action === 'fave') {
        text = 'Saved';
    }
    document.querySelector(".fave-status").textContent = text;
}

function setLikeCounter(action) {
    let text = document.querySelector(".like-counter").textContent.trim();
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
    document.querySelector(".like-counter").textContent = text;
}

async function performAction(action) {
    const url = `${window.location.pathname}${action}`;
    return await fetch(url, { method: 'POST' });
}

function listenForAction(action) {
    const action_element = document.querySelector(`.${action}`);
    action_element.addEventListener('click', (event) => {
        event.target.classList.toggle(`${action}-no`);
        event.target.classList.toggle(`${action}-yes`);
        let current_action = action;
        if (event.target.classList.contains(`${action}-no`)) {
            current_action = `un${action}`;
        }
        performAction(current_action)
            .then(response => {
                if (response.ok) {
                    if (current_action.includes('like')) {
                        setLikeCounter(current_action);
                    } else {
                        setFaveStatus(current_action);
                    }
                }
            });
    });
}

listenForAction('like');
listenForAction('fave');