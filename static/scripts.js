document.addEventListener('DOMContentLoaded', function() {
    // Initialize modals
    const customerRegistrationModal = new bootstrap.Modal(document.getElementById('customerRegistrationModal'));
    const commercialRegistrationModal = new bootstrap.Modal(document.getElementById('commercialRegistrationModal'));
    const verificationModal = new bootstrap.Modal(document.getElementById('verificationModal'));
    const otpVerificationModal = new bootstrap.Modal(document.getElementById('otpVerificationModal'));
    const customerDetailsModal = new bootstrap.Modal(document.getElementById('customerDetailsModal'));
    const emailOtpVerificationModal = new bootstrap.Modal(document.getElementById('emailOtpVerificationModal'));
    const otherDetailsModal = new bootstrap.Modal(document.getElementById('otherDetailsModal'));
    const customerDetailsReviewModal = new bootstrap.Modal(document.getElementById('customerDetailsReviewModal'));
    const registrationSuccessModal = new bootstrap.Modal(document.getElementById('registrationSuccessModal'));
    const loginModal = new bootstrap.Modal(document.getElementById('loginModal'));
    const loginOtpModal = new bootstrap.Modal(document.getElementById('loginOtpModal'));
    const commercialBusinessDetailsModal = new bootstrap.Modal(document.getElementById('commercialBusinessDetailsModal'));
    const commercialOtherDetailsModal = new bootstrap.Modal(document.getElementById('commercialOtherDetailsModal'));
    const otherRegistrationChoiceModal = new bootstrap.Modal(document.getElementById('otherRegistrationChoiceModal'));

    let registrationType = 'individual'; // default
    const locationData = {
        'kenya': {
            'Nairobi': ['Westlands', 'Dagoretti', 'Langata', 'Kibra', 'Kasarani', 'Embakasi', 'Makadara', 'Kamukunji', 'Starehe'],
            'Mombasa': ['Changamwe', 'Jomvu', 'Kisauni', 'Nyali', 'Likoni', 'Mvita'],
            'Kisumu': ['Kisumu Central', 'Kisumu East', 'Kisumu West', 'Seme', 'Nyando', 'Muhoroni', 'Nyakach'],
            'Nakuru': ['Nakuru East', 'Nakuru West', 'Naivasha', 'Gilgil', 'Molo', 'Rongai'],
            'Kiambu': ['Kiambu', 'Kikuyu', 'Limuru', 'Thika', 'Ruiru', 'Juja']
        },
        'uganda': {
            'Central': ['Kampala', 'Entebbe', 'Mukono', 'Wakiso'],
            'Western': ['Mbarara', 'Fort Portal', 'Kabale', 'Hoima'],
            'Eastern': ['Jinja', 'Mbale', 'Soroti', 'Tororo'],
            'Northern': ['Gulu', 'Lira', 'Arua', 'Moroto']
        },
        'tanzania': {
            'Dar es Salaam': ['Ilala', 'Kinondoni', 'Temeke', 'Kigamboni', 'Ubungo'],
            'Arusha': ['Arusha City', 'Arusha District', 'Meru', 'Karatu', 'Monduli'],
            'Zanzibar': ['Urban', 'West', 'North A', 'North B', 'Central', 'South']
        },
        'rwanda': {
            'Kigali': ['Nyarugenge', 'Gasabo', 'Kicukiro'],
            'Northern': ['Musanze', 'Gicumbi', 'Rulindo', 'Burera', 'Gakenke']
        },
        'burundi': {
            'Bujumbura Mairie': ['Muha', 'Mukaza', 'Ntahangwa'],
            'Gitega': ['Gitega', 'Bugendana', 'Bukirasazi', 'Buraza']
        },
        'DRC Congo': {
            'Kinshasa': ['Gombe', 'Kalamu', 'Limete', 'Ngaliema'],
            'Lumbumbashi': ['Kamalondo', 'Kenya', 'Katuba', 'Lumbumbashi']
        }
    };

    let selectedCountryName = '';
    let selectedCountryValue = '';

    const otherDetailsModalEl = document.getElementById('otherDetailsModal');
    const countySelect = document.getElementById('county');
    const townSelect = document.getElementById('town');
    const detailsCountry = document.getElementById('detailsCountry');

    if (otherDetailsModalEl) {
        otherDetailsModalEl.addEventListener('show.bs.modal', function () {
            // Populate country
            if (detailsCountry) {
                detailsCountry.value = selectedCountryName || 'Not Selected';
            }

            // Populate counties based on selected country
            if (countySelect) {
                // Clear existing options
                countySelect.innerHTML = '<option value="">Select County</option>';
                townSelect.innerHTML = '<option value="">Select Town</option>';

                const countryValue = selectedCountryValue;
                if (countryValue && locationData[countryValue]) {
                    const counties = Object.keys(locationData[countryValue]);
                    counties.sort().forEach(county => {
                        const option = document.createElement('option');
                        option.value = county;
                        option.textContent = county;
                        countySelect.appendChild(option);
                    });
                }
            }
        });
    }

    if (countySelect && townSelect) {
        countySelect.addEventListener('change', function () {
            const selectedCounty = this.value;
            const countryValue = selectedCountryValue;

            // Clear existing town options
            townSelect.innerHTML = '<option value="">Select Town</option>';

            if (selectedCounty && countryValue && locationData[countryValue][selectedCounty]) {
                const towns = locationData[countryValue][selectedCounty];
                towns.sort().forEach(town => {
                    const option = document.createElement('option');
                    option.value = town;
                    option.textContent = town;
                    townSelect.appendChild(option);
                });
            }
        });
    }

    // Registration selection logic handled via data-bs-toggle in HTML
    document.querySelectorAll('.registration-type-main-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            registrationType = this.dataset.type || 'individual';
            console.log('Capture registration type:', registrationType);
        });
    });

    // Handle commercial sub-types
    document.querySelectorAll('.commercial-type-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            registrationType = 'commercial';
        });
    });

    // Handle other sub-types
    document.querySelectorAll('.other-type-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            registrationType = 'other';
        });
    });

    // Country code selection
    const countrySelect = document.getElementById('country');
    const phoneCodeSpan = document.getElementById('phoneCode');
    
    if (countrySelect && phoneCodeSpan) {
        countrySelect.addEventListener('change', function() {
            const selectedOption = this.options[this.selectedIndex];
            const countryCode = selectedOption.dataset.code;
            phoneCodeSpan.textContent = `+${countryCode}`;
        });
    }

    // Verification form submission
    const verificationForm = document.getElementById('verificationForm');
    const detailsPhoneNumber = document.getElementById('detailsPhoneNumber');
    
    if (verificationForm) {
        verificationForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const countrySelect = document.getElementById('country');
            const phoneNumber = document.getElementById('phoneNumber').value;
            
            if (!countrySelect.value || !phoneNumber) {
                alert('Please fill in all fields');
                return;
            }
            
            const selectedOption = countrySelect.options[countrySelect.selectedIndex];
            selectedCountryValue = countrySelect.value;
            selectedCountryName = selectedOption.textContent.split('(')[0].trim();
            const countryCode = selectedOption.dataset.code;
            const formattedPhoneNumber = phoneNumber.replace(/\D/g, ''); // Remove all non-digit characters
            const fullPhoneNumber = `+${countryCode}${formattedPhoneNumber}`;
            
            if (detailsPhoneNumber) {
                detailsPhoneNumber.value = `+${countryCode} ${phoneNumber}`;
            }
            
            // Send OTP to backend
            fetch('/api/send-phone-otp/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    phone_number: fullPhoneNumber,
                    country: countrySelect.value,
                    registration_type: registrationType
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    verificationModal.hide();
                    setTimeout(() => otpVerificationModal.show(), 300);
                } else {
                    alert(data.message || 'Failed to send OTP');
                }
            })
            .catch(error => {
                console.error('Error sending OTP:', error);
                alert('An error occurred while sending OTP. Please try again.');
            });
        });
    }

    // Phone OTP resend functionality
    const phoneResendBtn = document.querySelector('#otpVerificationModal .btn-orange-full');
    if (phoneResendBtn) {
        phoneResendBtn.addEventListener('click', function(e) {
            e.preventDefault();
            
            const countrySelect = document.getElementById('country');
            const phoneNumber = document.getElementById('phoneNumber').value;
            
            const selectedOption = countrySelect.options[countrySelect.selectedIndex];
            const countryCode = selectedOption.dataset.code;
            const formattedPhoneNumber = phoneNumber.replace(/\D/g, ''); // Remove all non-digit characters
            const fullPhoneNumber = `+${countryCode}${formattedPhoneNumber}`;
            
            fetch('/api/send-phone-otp/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    phone_number: fullPhoneNumber,
                    country: countrySelect.value,
                    registration_type: registrationType
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Phone OTP resent successfully');
                } else {
                    alert(data.message || 'Failed to resend phone OTP');
                }
            })
            .catch(error => {
                console.error('Error resending phone OTP:', error);
                alert('An error occurred while resending phone OTP. Please try again.');
            });
        });
    }

    // OTP verification handling
    const otpInputs = document.querySelectorAll('.otp-input');
    
    otpInputs.forEach((input, index) => {
        input.addEventListener('input', function() {
            if (this.value.length === 1 && index < otpInputs.length - 1) {
                otpInputs[index + 1].focus();
            }
        });
        
        input.addEventListener('keydown', function(e) {
            if (e.key === 'Backspace' && this.value.length === 0 && index > 0) {
                otpInputs[index - 1].focus();
            }
        });
    });

    const otpVerificationForm = document.getElementById('otpVerificationForm');
    
    if (otpVerificationForm) {
        otpVerificationForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const otp = Array.from(otpInputs).map(input => input.value).join('');
            
            if (otp.length !== 4) {
                alert('Please enter all 4 digits');
                return;
            }
            
            // Verify OTP with backend
            const countrySelect = document.getElementById('country');
            const phoneNumber = document.getElementById('phoneNumber').value;
            const selectedOption = countrySelect.options[countrySelect.selectedIndex];
            const countryCode = selectedOption.dataset.code;
            const formattedPhoneNumber = phoneNumber.replace(/\D/g, ''); // Remove all non-digit characters
            const fullPhoneNumber = `+${countryCode}${formattedPhoneNumber}`;
            
            fetch('/api/verify-phone-otp/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    phone_number: fullPhoneNumber,
                    otp_code: otp
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    otpVerificationModal.hide();
                    setTimeout(() => {
                        if (registrationType === 'commercial' || registrationType === 'other') {
                            commercialBusinessDetailsModal.show();
                        } else {
                            customerDetailsModal.show();
                        }
                    }, 300);
                } else {
                    alert(data.message || 'Invalid OTP');
                }
            })
            .catch(error => {
                console.error('Error verifying OTP:', error);
                alert('An error occurred while verifying OTP. Please try again.');
            });
        });
    }

    // Customer details form submission
    const customerDetailsForm = document.getElementById('customerDetailsForm');
    const displayEmailSpan = document.getElementById('displayEmail');
    
    if (customerDetailsForm) {
        customerDetailsForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const firstName = document.getElementById('firstName').value;
            const middleName = document.getElementById('middleName').value;
            const lastName = document.getElementById('lastName').value;
            const email = document.getElementById('emailAddress').value;
            const phoneNumber = document.getElementById('detailsPhoneNumber').value;
            
            if (!firstName || !middleName || !lastName || !email) {
                alert('Please fill in all fields');
                return;
            }
            
            if (displayEmailSpan) {
                displayEmailSpan.textContent = email;
            }
            
            // Complete registration and send email OTP
            fetch('/api/complete-registration/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    phone_number: phoneNumber.replace(/\s/g, ''),
                    first_name: firstName,
                    middle_name: middleName,
                    last_name: lastName,
                    email: email
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    customerDetailsModal.hide();
                    setTimeout(() => emailOtpVerificationModal.show(), 300);
                } else {
                    alert(data.message || 'Failed to complete registration');
                }
            })
            .catch(error => {
                console.error('Error completing registration:', error);
                alert('An error occurred while completing registration. Please try again.');
            });
        });
    }

    // Email OTP resend functionality
    const emailResendBtn = document.querySelector('#emailOtpVerificationModal .btn-link');
    if (emailResendBtn) {
        emailResendBtn.addEventListener('click', function(e) {
            e.preventDefault();
            
            const email = document.getElementById('emailAddress').value || ( (registrationType === 'commercial' || registrationType === 'other') ? document.getElementById('businessEmail').value : '');
            
            fetch('/api/resend-email-otp/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    email: email
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Email OTP resent successfully');
                } else {
                    alert(data.message || 'Failed to resend email OTP');
                }
            })
            .catch(error => {
                console.error('Error resending email OTP:', error);
                alert('An error occurred while resending email OTP. Please try again.');
            });
        });
    }

    // Email OTP verification handling
    const emailOtpInputs = document.querySelectorAll('.email-otp-input');
    
    emailOtpInputs.forEach((input, index) => {
        input.addEventListener('input', function() {
            if (this.value.length === 1 && index < emailOtpInputs.length - 1) {
                emailOtpInputs[index + 1].focus();
            }
        });
        
        input.addEventListener('keydown', function(e) {
            if (e.key === 'Backspace' && this.value.length === 0 && index > 0) {
                emailOtpInputs[index - 1].focus();
            }
        });
    });

    const emailOtpVerificationForm = document.getElementById('emailOtpVerificationForm');
    
    if (emailOtpVerificationForm) {
        emailOtpVerificationForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const emailOtp = Array.from(emailOtpInputs).map(input => input.value).join('');
            
            if (emailOtp.length !== 4) {
                alert('Please enter all 4 digits');
                return;
            }
            
            // Verify email OTP with backend
            const email = document.getElementById('emailAddress').value || ( (registrationType === 'commercial' || registrationType === 'other') ? document.getElementById('businessEmail').value : '');
            
            fetch('/api/verify-email-otp/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    email: email,
                    otp_code: emailOtp
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    emailOtpVerificationModal.hide();
                    setTimeout(() => {
                        if (registrationType === 'commercial' || registrationType === 'other') {
                            commercialOtherDetailsModal.show();
                        } else {
                            otherDetailsModal.show();
                        }
                    }, 300);
                } else {
                    alert(data.message || 'Invalid OTP');
                }
            })
            .catch(error => {
                console.error('Error verifying email OTP:', error);
                alert('An error occurred while verifying email OTP. Please try again.');
            });
        });
    }

    // Other details form submission
    const otherDetailsForm = document.getElementById('otherDetailsForm');
    
    if (otherDetailsForm) {
        otherDetailsForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const idNumber = document.getElementById('idNumber').value;
            const pinNumber = document.getElementById('pinNumber').value;
            const address = document.getElementById('address').value;
            const county = document.getElementById('county').value;
            const town = document.getElementById('town').value;
            const passportPhoto = document.getElementById('passportPhoto').files[0];
            
            if (!idNumber || !pinNumber || !address || !county || !town || !passportPhoto) {
                alert('Please fill in all fields and upload a passport photo');
                return;
            }
            
            // Update review modal with collected data
            updateReviewModal();
            
            otherDetailsModal.hide();
            setTimeout(() => customerDetailsReviewModal.show(), 300);
        });
    }

    // Commercial business details form submission
    const commercialBusinessDetailsForm = document.getElementById('commercialBusinessDetailsForm');
    if (commercialBusinessDetailsForm) {
        commercialBusinessDetailsForm.addEventListener('submit', function(e) {
            e.preventDefault();

            if (!this.checkValidity()) {
                e.stopPropagation();
                this.classList.add('was-validated');
                return;
            }

            commercialBusinessDetailsModal.hide();

            const otpModalEl = document.getElementById('otpVerificationModal');
            const otpModalInstance = bootstrap.Modal.getInstance(otpModalEl);
            if (otpModalInstance) {
                otpModalInstance.hide();
            }

            emailOtpVerificationModal.hide();
            setTimeout(() => commercialOtherDetailsModal.show(), 300);
        });
    }

    // Populate town for commercial business details modal
    const commercialBusinessDetailsModalEl = document.getElementById('commercialBusinessDetailsModal');
    if (commercialBusinessDetailsModalEl) {
        commercialBusinessDetailsModalEl.addEventListener('show.bs.modal', function () {
            const businessTownSelect = document.getElementById('businessTown');
            if (businessTownSelect) {
                businessTownSelect.innerHTML = '<option value="">Town:</option>';
                const countryValue = selectedCountryValue;
                if (countryValue && locationData[countryValue]) {
                    const counties = Object.keys(locationData[countryValue]);
                    counties.forEach(county => {
                        const towns = locationData[countryValue][county];
                        towns.forEach(town => {
                            const option = document.createElement('option');
                            option.value = town;
                            option.textContent = town;
                            businessTownSelect.appendChild(option);
                        });
                    });
                }
            }
        });
    }

    // Commercial other details form submission
    const commercialOtherDetailsForm = document.getElementById('commercialOtherDetailsForm');
    if (commercialOtherDetailsForm) {
        commercialOtherDetailsForm.addEventListener('submit', function(e) {
            e.preventDefault();
            updateReviewModal();
            commercialOtherDetailsModal.hide();
            setTimeout(() => customerDetailsReviewModal.show(), 300);
        });
    }

    // Update review modal with collected data
    function updateReviewModal() {
        if (registrationType === 'commercial' || registrationType === 'other') {
            const businessName = document.getElementById('businessName').value;
            const industryType = document.getElementById('industryType').value;
            const contactName = document.getElementById('businessContactName').value;
            const contactNumber = document.getElementById('businessContactNumber').value;
            const emailAddress = document.getElementById('businessEmail').value;
            
            document.getElementById('reviewFirstName').textContent = businessName;
            document.getElementById('reviewLastName').textContent = industryType;
            document.getElementById('reviewMiddleName').textContent = contactName;
            document.getElementById('reviewPhoneNumber').textContent = contactNumber;
            document.getElementById('reviewEmailAddress').textContent = emailAddress;
            
            // Other fields
            document.getElementById('reviewIdNumber').textContent = document.getElementById('businessRegNumber').value;
            document.getElementById('reviewPinNumber').textContent = document.getElementById('commercialPinNumber').value;
            document.getElementById('reviewAddress').textContent = document.getElementById('businessAddress').value;
            document.getElementById('reviewCounty').textContent = 'Commercial';
            document.getElementById('reviewTown').textContent = document.getElementById('businessTown').value;
        } else {
            const firstName = document.getElementById('firstName').value;
            const middleName = document.getElementById('middleName').value;
            const lastName = document.getElementById('lastName').value;
            const phoneNumber = document.getElementById('detailsPhoneNumber').value;
            const emailAddress = document.getElementById('emailAddress').value;
            const idNumber = document.getElementById('idNumber').value;
            const pinNumber = document.getElementById('pinNumber').value;
            const address = document.getElementById('address').value;
            const county = document.getElementById('county').value;
            const town = document.getElementById('town').value;
            
            document.getElementById('reviewFirstName').textContent = firstName;
            document.getElementById('reviewLastName').textContent = lastName;
            document.getElementById('reviewMiddleName').textContent = middleName || '-';
            document.getElementById('reviewPhoneNumber').textContent = phoneNumber;
            document.getElementById('reviewEmailAddress').textContent = emailAddress;
            document.getElementById('reviewIdNumber').textContent = idNumber;
            document.getElementById('reviewPinNumber').textContent = pinNumber;
            document.getElementById('reviewAddress').textContent = address;
            document.getElementById('reviewCounty').textContent = county;
            document.getElementById('reviewTown').textContent = town;
        }

        const passportPhoto = (registrationType === 'commercial' || registrationType === 'other') ? null : document.getElementById('passportPhoto').files[0];
        
        // Handle Passport Preview
        const reviewPreview = document.getElementById('reviewPassportPreview');
        const placeholderIcon = document.getElementById('photoPlaceholderIcon');
        
        if (passportPhoto && reviewPreview) {
            const reader = new FileReader();
            reader.onload = function(e) {
                reviewPreview.src = e.target.result;
                reviewPreview.style.display = 'block';
                if (placeholderIcon) placeholderIcon.style.display = 'none';
            }
            reader.readAsDataURL(passportPhoto);
        } else {
            if (reviewPreview) reviewPreview.style.display = 'none';
            if (placeholderIcon) placeholderIcon.style.display = 'flex';
        }
    }

    // Re-upload from review modal
    const previewPhotoContainer = document.getElementById('previewPhotoContainer');
    const reuploadInput = document.getElementById('reuploadPassport');
    const mainPassportInput = document.getElementById('passportPhoto');

    if (previewPhotoContainer && reuploadInput) {
        previewPhotoContainer.addEventListener('click', () => {
            reuploadInput.click();
        });

        reuploadInput.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                const file = this.files[0];
                
                // Sync to main input
                if (mainPassportInput) {
                    const dataTransfer = new DataTransfer();
                    dataTransfer.items.add(file);
                    mainPassportInput.files = dataTransfer.files;
                }

                // Update preview immediately
                const reviewPreview = document.getElementById('reviewPassportPreview');
                const placeholderIcon = document.getElementById('photoPlaceholderIcon');
                const reader = new FileReader();
                reader.onload = function(e) {
                    reviewPreview.src = e.target.result;
                    reviewPreview.style.display = 'block';
                    if (placeholderIcon) placeholderIcon.style.display = 'none';
                }
                reader.readAsDataURL(file);
            }
        });
    }

    // Submit registration (Confirm Details -> T&C)
    const submitRegistrationBtn = document.getElementById('submitRegistration');
    const termsConditionsModal = new bootstrap.Modal(document.getElementById('termsConditionsModal'));
    
    if (submitRegistrationBtn) {
        submitRegistrationBtn.addEventListener('click', function() {
            const currentModal = bootstrap.Modal.getInstance(document.getElementById('customerDetailsReviewModal'));
            if (currentModal) currentModal.hide();
            setTimeout(() => {
                termsConditionsModal.show();
            }, 300);
        });
    }

    // Final Submit (T&C -> Success)
    const finalSubmitBtn = document.getElementById('finalSubmitBtn');
    if (finalSubmitBtn) {
        finalSubmitBtn.addEventListener('click', function() {
            const acceptTerms = document.getElementById('acceptTerms');
            if (!acceptTerms || !acceptTerms.checked) {
                alert('Please accept the Terms & Conditions to proceed.');
                return;
            }

            // Collect all details to save
            const phoneNumber = document.getElementById('detailsPhoneNumber').value.replace(/\s/g, '');
            const isBusiness = (registrationType === 'commercial' || registrationType === 'other');
            const idNumber = isBusiness ? document.getElementById('businessRegNumber').value : document.getElementById('idNumber').value;
            const pinNumber = isBusiness ? document.getElementById('commercialPinNumber').value : document.getElementById('pinNumber').value;
            const address = isBusiness ? document.getElementById('businessAddress').value : document.getElementById('address').value;
            const county = isBusiness ? 'Commercial' : document.getElementById('county').value;
            const town = isBusiness ? document.getElementById('businessTown').value : document.getElementById('town').value;
            
            // Show loading state or similar if needed
            finalSubmitBtn.disabled = true;
            finalSubmitBtn.textContent = 'Submitting...';

            fetch('/api/complete-other-details/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    phone_number: phoneNumber,
                    id_number: idNumber,
                    pin_number: pinNumber,
                    address: address,
                    county: county,
                    town: town
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const currentModal = bootstrap.Modal.getInstance(document.getElementById('termsConditionsModal'));
                    if (currentModal) currentModal.hide();
                    
                    setTimeout(() => {
                        const firstName = isBusiness ? document.getElementById('businessName').value : document.getElementById('firstName').value;
                        const lastName = isBusiness ? '' : document.getElementById('lastName').value;
                        const finalSuccessName = document.getElementById('finalSuccessName');
                        if (finalSuccessName) {
                            finalSuccessName.textContent = firstName + (lastName ? ' ' + lastName : '');
                        }
                        registrationSuccessModal.show();
                        
                        // Also redirect automatically after 3 seconds
                        setTimeout(() => {
                            window.location.href = data.redirect_url || '/dashboard/';
                        }, 3000);
                    }, 300);
                } else {
                    alert(data.message || 'Failed to save final details. Please try again.');
                    finalSubmitBtn.disabled = false;
                    finalSubmitBtn.textContent = 'Submit';
                }
            })
            .catch(error => {
                console.error('Error saving final details:', error);
                alert('An error occurred. Please try again.');
                finalSubmitBtn.disabled = false;
                finalSubmitBtn.textContent = 'Submit';
            });
        });
    }

    // Redirect to dashboard
    const redirectToDashboardBtn = document.getElementById('redirectToDashboard');
    
    if (redirectToDashboardBtn) {
        redirectToDashboardBtn.addEventListener('click', function() {
            registrationSuccessModal.hide();
            // Redirect to dashboard
            window.location.href = '/dashboard/';
        });
    }

    // Login form submission
    const loginForm = document.getElementById('loginForm');
    
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const loginPhoneNumber = document.getElementById('loginPhoneNumber').value;
            
            if (!loginPhoneNumber) {
                alert('Please enter your phone number');
                return;
            }
            
            // Send login OTP to backend
            fetch('/api/send-login-otp/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    phone_number: loginPhoneNumber
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    loginModal.hide();
                    setTimeout(() => loginOtpModal.show(), 300);
                } else {
                    alert(data.message || 'Failed to send login OTP');
                }
            })
            .catch(error => {
                console.error('Error sending login OTP:', error);
                alert('An error occurred while sending login OTP. Please try again.');
            });
        });
    }

    // Login OTP handling
    const loginOtpInputs = document.querySelectorAll('.login-otp-input');
    
    loginOtpInputs.forEach((input, index) => {
        input.addEventListener('input', function() {
            if (this.value.length === 1 && index < loginOtpInputs.length - 1) {
                loginOtpInputs[index + 1].focus();
            }
        });
        
        input.addEventListener('keydown', function(e) {
            if (e.key === 'Backspace' && this.value.length === 0 && index > 0) {
                loginOtpInputs[index - 1].focus();
            }
        });
    });

    const loginOtpForm = document.getElementById('loginOtpForm');
    
    if (loginOtpForm) {
        loginOtpForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const loginOtp = Array.from(loginOtpInputs).map(input => input.value).join('');
            
            if (loginOtp.length !== 4) {
                alert('Please enter all 4 digits');
                return;
            }
            
            // Verify login OTP with backend
            const loginPhoneNumber = document.getElementById('loginPhoneNumber').value;
            
            fetch('/api/verify-login-otp/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    phone_number: loginPhoneNumber,
                    otp_code: loginOtp
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    loginOtpModal.hide();
                    // Redirect to dashboard
                    window.location.href = data.redirect_url || '/dashboard';
                } else {
                    alert(data.message || 'Invalid OTP');
                }
            })
            .catch(error => {
                console.error('Error verifying login OTP:', error);
                alert('An error occurred while verifying login OTP. Please try again.');
            });
        });
    }

    console.log('Modal functionality initialized');
});
