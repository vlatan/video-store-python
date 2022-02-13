// Get references to the dom elements
var scroller = document.querySelector("#scroller");
var template = document.querySelector('#post_template');
var sentinel = document.querySelector('#sentinel');
var spinner = document.querySelector('#spinner');
// apply spinner
spinner.classList.add('spinner');
// Use infinite scroll from the second page onwards
var page = 2;
// There are still posts to be fetched
var the_end = false;

// Function to request new items and render to the dom
async function loadItems(url = '', data = {}) {

    // Use fetch to request data by passing the page number via POST method
    await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    }).then((response) => {

        if (!response.ok) {
            the_end = true;
            return
        }

        // Convert the response data to JSON
        response.json().then((data) => {

            // If empty JSON, exit the function
            if (!data.length) {
                // Replace the spinner with "No more posts"
                sentinel.innerHTML = "No more posts";
                // We got to the end, no more posts
                the_end = true;
                return;
            }

            // Iterate over the items in the response
            for (var i = 0; i < data.length; i++) {

                // Clone the HTML template
                let template_clone = template.content.cloneNode(true);

                // Query & update the template content
                template_clone.querySelector('.video-link').href = `/video/${data[i]['video_id']}/`;
                let thumb = template_clone.querySelector('.video-img');
                thumb.src = data[i]['thumbnails']['medium']['url'];
                thumb.alt = data[i]['title'];
                template_clone.querySelector('.video-title').innerHTML = data[i]['title'];
                let remove = template_clone.querySelector('.remove-option');
                if (remove) {
                    remove.setAttribute('data-id', `${data[i]['id']}`)
                }

                // Append template to dom
                scroller.appendChild(template_clone);
            }

            // Increment the page counter
            page += 1;
        })
    })
}

if ('IntersectionObserver' in window) {
    // Create a new IntersectionObserver instance
    let intersectionObserver = new IntersectionObserver(([entry]) => {
        // If there are still posts and the entry is intersecting
        if (the_end === false && entry.isIntersecting) {
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