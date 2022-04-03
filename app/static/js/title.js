// Edit Title
var editTitle = document.querySelector('.edit-title');
editTitle.addEventListener('click', () => {
    var videoTitle = document.querySelector('.video-title');
    if (editTitle.innerHTML === "Edit Title") {
        videoTitle.contentEditable = true;
        videoTitle.focus();
        editTitle.innerHTML = "Save";
    } else {
        const url = `${window.location.pathname}edit`;
        PostData(url, { title: videoTitle.innerHTML })
            .then(response => {
                if (response.ok) {
                    SetAlert("Title succesfully edited!");
                } else {
                    SetAlert("Sorry, something went wrong!");
                }
            });
        videoTitle.contentEditable = false;
        editTitle.innerHTML = "Edit Title";
    }
});