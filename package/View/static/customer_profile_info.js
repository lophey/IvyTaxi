let addpayment = document.getElementById('addpay');
let addpaymentbutton = addpayment.querySelector('.addpaymentbutton');

addpaymentbutton.onclick = function() {
    addpayment.classList.toggle('open');
};


let addaddress = document.getElementById('addadr');
let addaddressbutton = addaddress.querySelector('.addaddressbutton');

addaddressbutton.onclick = function() {
    addaddress.classList.toggle('open');
};

