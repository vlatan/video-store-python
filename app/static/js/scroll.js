// Get references to the dom elements
const scroller = document.getElementById("scroller");
const template = document.getElementById("post_template");
const sentinel = document.getElementById("sentinel");
const spinner = document.getElementById("spinner");
let page = 2; // Use infinite scroll from the second page onwards
let nextPage = true; // Assume there is next page to load


const noMoreScroll = () => {
    // Replace the spinner with "No more videos"
    sentinel.innerHTML = "No more videos";
    nextPage = false;
    return
};

// Function to request new items and render to the dom
const loadItems = (url = '', data = {}) => {

    postData(url, data).then(response => {

        // If bad response exit the function
        if (!response.ok) {
            return noMoreScroll();
        }

        // Convert the response data to JSON
        response.json().then(data => {

            // If empty JSON, exit the function
            if (!data.length) {
                return noMoreScroll();
            }

            // Iterate over the items in the response
            for (const item of data) {

                // Clone the HTML template
                const template_clone = template.content.cloneNode(true);

                // Query & update the template content
                template_clone.querySelector('.video-link').href = `/video/${item.video_id}/`;
                const thumb = template_clone.querySelector('.video-img');
                thumb.src = item.thumbnails.medium.url;
                thumb.alt = item.title;
                template_clone.querySelector('.video-title').innerHTML = item.title;
                const remove = template_clone.querySelector('.remove-option');
                if (remove) {
                    remove.setAttribute('data-id', `${item.id}`)
                }

                // Append template to dom
                scroller.appendChild(template_clone);
            }

            // Increment the page counter
            page += 1;
        })
    })
};

if ('IntersectionObserver' in window) {
    // Create a new IntersectionObserver instance
    let intersectionObserver = new IntersectionObserver(([entry]) => {
        // If there are still videos and the entry is intersecting
        if (nextPage && entry.isIntersecting) {
            // Call the loadItems function
            loadItems(`${window.location.href}`, { page: page });
            // Unobserve the entry
            // intersectionObserver.unobserve(entry);
        }
        // add root margin for earlier intersection detecetion
    }, { rootMargin: "100px 0px" });

    // Instruct the IntersectionObserver to watch the sentinel
    intersectionObserver.observe(sentinel);
}