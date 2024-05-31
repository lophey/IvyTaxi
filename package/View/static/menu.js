document.getElementById('menuButton').onclick = function() {
    var menu = document.getElementById('menu');
    var menuButton = document.getElementById('menuButton');
    var taxiOrder = document.getElementById('taxiOrder');
    if (menu.style.width === '250px') {
        menu.style.width = '0';
        menuButton.style.left = '0';
        taxiOrder.style.left = '50px';
    } else {
        menu.style.width = '250px';
        menuButton.style.left = '211px';
        taxiOrder.style.left = '262px';
    }

};