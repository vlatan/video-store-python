// Edit Title
var editTitle = document.querySelector('.edit-title');
var videoTitle = document.querySelector('.video-title');
const originalTitle = videoTitle.innerHTML;
editTitle.addEventListener('click', () => {
    if (editTitle.innerHTML === "Edit Title") {
        videoTitle.contentEditable = true;
        videoTitle.focus();
        editTitle.innerHTML = "Save Title";
    } else {
        const url = `${window.location.pathname}edit`;
        PostData(url, { title: videoTitle.innerHTML })
            .then(response => {
                if (response.ok) {
                    SetAlert("Title succesfully edited!");
                } else {
                    videoTitle.innerHTML = originalTitle;
                    SetAlert("Sorry, something went wrong!");
                }
            });
        videoTitle.contentEditable = false;
        editTitle.innerHTML = "Edit Title";
    }
});