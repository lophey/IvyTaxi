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

let paymentselect = document.getElementById('paymentslct');
let paymentselectbutton = paymentselect.querySelector('.paymentselectbutton');

paymentselectbutton.onclick = function() {
    paymentselect.classList.toggle('open');
};

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

    // Hidden inputs for start address components
    const startCityInput = document.getElementById('start_city');
    const startStreetInput = document.getElementById('start_street');
    const startHouseNumberInput = document.getElementById('start_house_number');

    // Hidden inputs for final address components
    const finalCityInput = document.getElementById('final_city');
    const finalStreetInput = document.getElementById('final_street');
    const finalHouseNumberInput = document.getElementById('final_house_number');

    const originAutocomplete = new google.maps.places.Autocomplete(originInput);
    const destinationAutocomplete = new google.maps.places.Autocomplete(destinationInput);

    originAutocomplete.bindTo('bounds', map);
    destinationAutocomplete.bindTo('bounds', map);

    // Получаем сохраненные адреса
    const savedAddressesElements = document.querySelectorAll("#saved-addresses-data span");
    const savedAddresses = Array.from(savedAddressesElements).map(el => el.getAttribute("data-address"));



    const geocoder = new google.maps.Geocoder();
    const originMarker = createMarker(map, "A");
    const destinationMarker = createMarker(map, "B");

    setupPlaceChangedListener(originAutocomplete, originMarker, originInput, map, 'start');
    setupPlaceChangedListener(destinationAutocomplete, destinationMarker, destinationInput, map, 'final');

    map.addListener('click', (event) => handleMapClick(event, originMarker, destinationMarker, originInput, destinationInput));

    originMarker.addListener('dragend', (event) => geocodePosition(geocoder, event.latLng, originInput, 'start'));
    destinationMarker.addListener('dragend', (event) => geocodePosition(geocoder, event.latLng, destinationInput, 'final'));

    function createMarker(map, label) {
        return new google.maps.Marker({
            map: map,
            draggable: true,
            label: label
        });
    }

    function setupPlaceChangedListener(autocomplete, marker, input, map, type) {
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

            // Set hidden inputs for city, street, and house number based on type (start/final)
            setHiddenInputs(place, type);
        });
    }

    function handleMapClick(event, originMarker, destinationMarker, originInput, destinationInput) {
        if (!originMarker.getPosition()) {
            placeMarker(event.latLng, originMarker, originInput, 'start');
        } else if (!destinationMarker.getPosition()) {
            placeMarker(event.latLng, destinationMarker, destinationInput, 'final');
        }
    }

    function placeMarker(location, marker, input, type) {
        marker.setPosition(location);
        geocodePosition(new google.maps.Geocoder(), location, input, type);
    }

    function geocodePosition(geocoder, position, input, type) {
        geocoder.geocode({ 'location': position }, (results, status) => {
            if (status === 'OK') {
                if (results[0]) {
                    input.value = formatAddress(results[0]);

                    // Set hidden inputs for city, street, and house number based on type (start/final)
                    setHiddenInputs(results[0], type);
                } else {
                    alert('No results found');
                }
            } else {
                alert('Geocoder failed due to: ' + status);
            }
        });
    }

    function setHiddenInputs(place, type) {
        const components = place.address_components || [];
        let city = '', street = '', houseNumber = '';

        components.forEach(component => {
            const types = component.types;
            if (types.includes('locality')) city = component.long_name;
            if (types.includes('route')) street = component.long_name;
            if (types.includes('street_number')) houseNumber = component.long_name;
        });

        if (type === 'start') {
            startCityInput.value = city;
            startStreetInput.value = street;
            startHouseNumberInput.value = houseNumber;
        } else if (type === 'final') {
            finalCityInput.value = city;
            finalStreetInput.value = street;
            finalHouseNumberInput.value = houseNumber;
        }
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

    // // Показ сохраненных адресов в выпадающем списке
    // originInput.addEventListener("input", () => {
    //     const inputValue = originInput.value.toLowerCase();
    //     const suggestionsContainer = document.getElementById("suggestions-container");
    //     suggestionsContainer.classList.add("suggestions-below");
    //     // // Если поле ввода пустое, очищаем контейнер с предложениями и выходим
    //     // if (!inputValue) {
    //     //     suggestionsContainer.innerHTML = "";
    //     //     return;
    //     // }
    //
    //     // Очистка предыдущих предложений
    //     suggestionsContainer.innerHTML = "";
    //
    //     // Показ только подходящих сохраненных адресов
    //     savedAddresses.forEach(address => {
    //         if (address.toLowerCase().includes(inputValue)) {
    //             const option = document.createElement("div");
    //             option.textContent = address;
    //             option.classList.add("suggestion");
    //             option.addEventListener("click", () => {
    //                 originInput.value = address;
    //                 suggestionsContainer.innerHTML = "";
    //             });
    //             suggestionsContainer.appendChild(option);
    //         }
    //     });
    // });

    const originSuggestionsContainer = document.getElementById("origin-suggestions-container");
    const destinationSuggestionsContainer = document.getElementById("destination-suggestions-container");

// Функция для показа предложений
    function showSuggestions(suggestionsContainer, filteredAddresses) {
        // Очистка предыдущих предложений
        suggestionsContainer.innerHTML = "";

        // Показ только подходящих сохраненных адресов
        filteredAddresses.forEach(address => {
            const option = document.createElement("div");
            option.textContent = address;
            option.classList.add("suggestion");
            option.addEventListener("click", () => {
                // Установка выбранного адреса в поле ввода
                if (suggestionsContainer === originSuggestionsContainer) {
                    originInput.value = address;
                } else {
                    destinationInput.value = address;
                }
                suggestionsContainer.innerHTML = ""; // Очистка предложений после выбора
            });
            suggestionsContainer.appendChild(option);
        });
    }

// Показ всех сохраненных адресов при фокусе на поле ввода начального адреса
    originInput.addEventListener("focus", () => {
        showSuggestions(originSuggestionsContainer, savedAddresses);
    });

// Фильтрация адресов при вводе текста в поле начального адреса
    originInput.addEventListener("input", () => {
        const inputValue = originInput.value.toLowerCase();

        if (!inputValue) {
            showSuggestions(originSuggestionsContainer, savedAddresses); // Показываем все адреса, если поле пустое
        } else {
            // Фильтрация и показ только подходящих адресов
            const filteredAddresses = savedAddresses.filter(address =>
                address.toLowerCase().includes(inputValue)
            );
            showSuggestions(originSuggestionsContainer, filteredAddresses);
        }
    });

// Показ всех сохраненных адресов при фокусе на поле ввода конечного адреса
    destinationInput.addEventListener("focus", () => {
        showSuggestions(destinationSuggestionsContainer, savedAddresses);
    });

// Фильтрация адресов при вводе текста в поле конечного адреса
    destinationInput.addEventListener("input", () => {
        const inputValue = destinationInput.value.toLowerCase();

        if (!inputValue) {
            showSuggestions(destinationSuggestionsContainer, savedAddresses); // Показываем все адреса, если поле пустое
        } else {
            // Фильтрация и показ только подходящих адресов
            const filteredAddresses = savedAddresses.filter(address =>
                address.toLowerCase().includes(inputValue)
            );
            showSuggestions(destinationSuggestionsContainer, filteredAddresses);
        }
    });

// Скрытие предложений, если поле теряет фокус
    function setupBlurEvent(input, suggestionsContainer) {
        input.addEventListener("blur", () => {
            setTimeout(() => {
                suggestionsContainer.innerHTML = ""; // Удаление предложений с небольшой задержкой
            }, 200);
        });
    }

    setupBlurEvent(originInput, originSuggestionsContainer);
    setupBlurEvent(destinationInput, destinationSuggestionsContainer);
}

