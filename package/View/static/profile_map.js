//                                  GOOGLE MAP SCRIPTS
function initMap() {
    const map = new google.maps.Map(document.getElementById('map'), {
        center: { lat: 46.46862346278983, lng: 30.730422522819932 },
        disableDefaultUI: true,
        zoomControl: true,
        zoom: 13
    });

    const originInput = document.getElementById('origin-input');

    // Hidden inputs for start address components
    const cityInput = document.getElementById('city');
    const streetInput = document.getElementById('street');
    const houseNumberInput = document.getElementById('house_number');

    const originAutocomplete = new google.maps.places.Autocomplete(originInput);

    originAutocomplete.bindTo('bounds', map);

    const geocoder = new google.maps.Geocoder();
    const originMarker = createMarker(map);

    setupPlaceChangedListener(originAutocomplete, originMarker, originInput, map);

    map.addListener('click', (event) => handleMapClick(event, originMarker, originInput));

    originMarker.addListener('dragend', (event) => geocodePosition(geocoder, event.latLng, originInput));

    function createMarker(map) {
        return new google.maps.Marker({
            map: map,
            draggable: true,
        });
    }

    function setupPlaceChangedListener(autocomplete, marker, input, map) {
        autocomplete.addListener('place_changed', () => {
            const place = autocomplete.getPlace();
            // if (!place.geometry) {
            //     alert(`No details available for input: '${place.name}'`);
            //     return;
            // }
            map.setCenter(place.geometry.location);
            map.setZoom(13);
            marker.setPosition(place.geometry.location);
            input.value = formatAddress(place);

            // Set hidden inputs for city, street, and house number based on type (start/final)
            setHiddenInputs(place);
        });
    }

    function handleMapClick(event, originMarker, originInput) {
        if (!originMarker.getPosition()) {
            placeMarker(event.latLng, originMarker, originInput);
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

                    // Set hidden inputs for city, street, and house number based on type (start/final)
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

