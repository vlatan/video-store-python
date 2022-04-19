// Edit Description
var editDescriptionButton = document.querySelector('.edit-description');
var unpublishedWrap = document.querySelector('.unpublished');
var videoDescription = document.querySelector('.video-description');
var originalDescription = videoDescription.innerText;


editDescriptionButton.addEventListener('click', () => {
    videoDescription.classList.toggle('editing');
    if (editDescriptionButton.innerText === "Edit Desc") {
        videoDescription.contentEditable = true;
        videoDescription.focus();
        editDescriptionButton.innerText = "Save Desc";
    } else {
        const url = `${window.location.pathname}edit`;
        PostData(url, { description: videoDescription.innerText })
            .then(response => {
                if (response.ok) {
                    SetAlert("Description succesfully published!");
                    originalDescription = videoDescription.innerText;
                    unpublishedWrap.replaceWith(videoDescription);
                } else {
                    videoDescription.innerText = originalDescription;
                    SetAlert("Sorry, something went wrong!");
                }
            });
        videoDescription.removeAttribute('contenteditable');
        videoDescription.blur();
        editDescriptionButton.innerText = "Edit Desc";
    }
});


function resetDescription(description, button) {
    description.removeAttribute('contenteditable');
    button.innerText = "Edit Desc";
    description.classList.remove('editing');
    description.innerText = originalDescription;
}


videoDescription.addEventListener('keydown', (e) => {
    if (e.code === 'Escape') {
        resetDescription(videoDescription, editDescriptionButton);
    }
});


document.addEventListener('click', (e) => {
    if (e.target !== editDescriptionButton &&
        e.target !== videoDescription &&
        videoDescription.classList.contains('editing')) {
        resetDescription(videoDescription, editDescriptionButton);
    }
});