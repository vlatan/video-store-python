// Edit Title
var editTitleButton = document.querySelector('.edit-title');
var videoTitle = document.querySelector('.video-title');
const originalTitle = videoTitle.innerText;

editTitleButton.addEventListener('click', () => {
    videoTitle.classList.toggle('editing');
    if (editTitleButton.innerText === "Edit Title") {
        videoTitle.contentEditable = true;
        videoTitle.focus();
        editTitleButton.innerText = "Save Title";
    } else {
        const url = `${window.location.pathname}edit`;
        PostData(url, { title: videoTitle.innerText })
            .then(response => {
                if (response.ok) {
                    SetAlert("Title succesfully edited!");
                } else {
                    videoTitle.innerText = originalTitle;
                    SetAlert("Sorry, something went wrong!");
                }
            });
        videoTitle.contentEditable = false;
        editTitleButton.innerText = "Edit Title";
    }
});

videoTitle.addEventListener('keydown', (e) => {
    if (e.code === 'Escape') {
        videoTitle.contentEditable = false;
        editTitleButton.innerText = "Edit Title";
        videoTitle.classList.remove('editing');
        videoTitle.innerText = originalTitle;
    }
});

document.addEventListener('click', (e) => {
    var editingTitle = document.querySelector('.editing');
    if (e.target !== editTitleButton && e.target !== editingTitle) {
        videoTitle.contentEditable = false;
        editTitleButton.innerText = "Edit Title";
        videoTitle.classList.remove('editing');
        videoTitle.innerText = originalTitle;
    }
});