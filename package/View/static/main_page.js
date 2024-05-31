//                                  ORDER MENU SCRIPTS
document.addEventListener('DOMContentLoaded', function() {
    var submitBtn = document.getElementById('submit_btn');

    submitBtn.addEventListener('click', function() {
        submitBtn.classList.add('onclic');
        setTimeout(validate, 250);
    });

    function validate() {
        setTimeout(function() {
            submitBtn.classList.remove('onclic');
            submitBtn.classList.add('validate');
            setTimeout(callback, 450);
        }, 2250);
    }

    function callback() {
        setTimeout(function() {
            submitBtn.classList.remove('validate');
        }, 1250);
    }
});

//                                  GOOGLE MAP SCRIPTS
function initMap() {
    const map = new google.maps.Map(document.getElementById('map'), {
        center: { lat: 46.46862346278983, lng: 30.730422522819932 },
        disableDefaultUI: true,
        zoomControl: true,
        zoom: 13
    });

    const originInput = document.getElementById('origin-input');
    const destinationInput = document.getElementById('destination-input');

    const cityInput = document.getElementById('city');
    const streetInput = document.getElementById('street');
    const houseNumberInput = document.getElementById('house_number');

    const originAutocomplete = new google.maps.places.Autocomplete(originInput);
    const destinationAutocomplete = new google.maps.places.Autocomplete(destinationInput);

    originAutocomplete.bindTo('bounds', map);
    destinationAutocomplete.bindTo('bounds', map);

    const geocoder = new google.maps.Geocoder();
    const originMarker = createMarker(map, "A");
    const destinationMarker = createMarker(map, "B");

    setupPlaceChangedListener(originAutocomplete, originMarker, originInput, map);
    setupPlaceChangedListener(destinationAutocomplete, destinationMarker, destinationInput, map);

    map.addListener('click', (event) => handleMapClick(event, originMarker, destinationMarker, originInput, destinationInput));

    originMarker.addListener('dragend', (event) => geocodePosition(geocoder, event.latLng, originInput));
    destinationMarker.addListener('dragend', (event) => geocodePosition(geocoder, event.latLng, destinationInput));

    function createMarker(map, label) {
        return new google.maps.Marker({
            map: map,
            draggable: true,
            label: label
        });
    }

    function setupPlaceChangedListener(autocomplete, marker, input, map) {
        autocomplete.addListener('place_changed', () => {
            const place = autocomplete.getPlace();
            if (!place.geometry) {
                alert(`No details available for input: '${place.name}'`);
                return;
            }
            map.setCenter(place.geometry.location);
            map.setZoom(13);
            marker.setPosition(place.geometry.location);
            input.value = formatAddress(place);

            // Set hidden inputs for city, street, and house number
            setHiddenInputs(place);
        });
    }

    function handleMapClick(event, originMarker, destinationMarker, originInput, destinationInput) {
        if (!originMarker.getPosition()) {
            placeMarker(event.latLng, originMarker, originInput);
        } else if (!destinationMarker.getPosition()) {
            placeMarker(event.latLng, destinationMarker, destinationInput);
        }
    }

    function placeMarker(location, marker, input) {
        marker.setPosition(location);
        geocodePosition(new google.maps.Geocoder(), location, input);
    }

    function geocodePosition(geocoder, position, input) {
        geocoder.geocode({ 'location': position }, (results, status) => {
            if (status === 'OK') {
                if (results[0]) {
                    input.value = formatAddress(results[0]);

                    // Set hidden inputs for city, street, and house number
                    setHiddenInputs(results[0]);
                } else {
                    alert('No results found');
                }
            } else {
                alert('Geocoder failed due to: ' + status);
            }
        });
    }

    function setHiddenInputs(place) {
        const components = place.address_components || [];
        let city = '', street = '', houseNumber = '';

        components.forEach(component => {
            const types = component.types;
            if (types.includes('locality')) city = component.long_name;
            if (types.includes('route')) street = component.long_name;
            if (types.includes('street_number')) houseNumber = component.long_name;
        });

        cityInput.value = city;
        streetInput.value = street;
        houseNumberInput.value = houseNumber;
    }

    function formatAddress(place) {
        const components = place.address_components || [];
        let city = '', street = '', houseNumber = '';

        components.forEach(component => {
            const types = component.types;
            if (types.includes('locality')) city = component.long_name;
            if (types.includes('route')) street = component.long_name;
            if (types.includes('street_number')) houseNumber = component.long_name;
        });

        return [city, street, houseNumber].filter(Boolean).join(', ');
    }
}
