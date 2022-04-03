// Edit Title
var editTitle = document.querySelector('.edit-title');
var videoTitle = document.querySelector('.video-title');
const originalTitle = videoTitle.innerText;
editTitle.addEventListener('click', () => {
    if (editTitle.innerText === "Edit Title") {
        videoTitle.contentEditable = true;
        videoTitle.focus();
        editTitle.innerText = "Save Title";
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
        editTitle.innerText = "Edit Title";
    }
});