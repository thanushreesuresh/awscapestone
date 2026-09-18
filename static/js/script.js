// ==========================================================================
// Student Registration Frontend Client Script
// ==========================================================================
document.addEventListener('DOMContentLoaded', () => {
    const photoInput = document.getElementById('photo');
    const dropZone = document.getElementById('drop-zone');
    const previewContainer = document.getElementById('file-preview-container');
    const previewImg = document.getElementById('photo-preview');
    const previewFilename = document.getElementById('preview-filename');
    const removePhotoBtn = document.getElementById('remove-photo-btn');
    const form = document.querySelector('.registration-form');

    // --------------------------------------------------------------------------
    // Photo Preview & File Selection Handling
    // --------------------------------------------------------------------------
    if (photoInput && previewContainer) {
        photoInput.addEventListener('change', (e) => {
            const file = e.target.files && e.target.files[0];
            handleFileSelection(file);
        });

        // Drag & drop interactions
        if (dropZone) {
            ['dragenter', 'dragover'].forEach(eventName => {
                dropZone.addEventListener(eventName, (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    dropZone.classList.add('drag-over');
                }, false);
            });

            ['dragleave', 'drop'].forEach(eventName => {
                dropZone.addEventListener(eventName, (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    dropZone.classList.remove('drag-over');
                }, false);
            });

            dropZone.addEventListener('drop', (e) => {
                const dt = e.dataTransfer;
                const files = dt.files;
                if (files && files.length > 0) {
                    photoInput.files = files;
                    handleFileSelection(files[0]);
                }
            });
        }

        // Remove selected photo
        if (removePhotoBtn) {
            removePhotoBtn.addEventListener('click', () => {
                photoInput.value = '';
                previewContainer.classList.add('hidden');
                previewImg.src = '#';
                previewFilename.textContent = '';
                dropZone.classList.remove('hidden');
            });
        }
    }

    function handleFileSelection(file) {
        if (!file) return;

        // Check if the selected file is an image
        if (!file.type.startsWith('image/')) {
            alert('Please select a valid image file (JPG, PNG, WEBP).');
            photoInput.value = '';
            return;
        }

        const reader = new FileReader();
        reader.onload = (e) => {
            previewImg.src = e.target.result;
            previewFilename.textContent = file.name;
            previewContainer.classList.remove('hidden');
        };
        reader.readAsDataURL(file);
    }

    // --------------------------------------------------------------------------
    // Basic Form Validation & Field State Handling
    // --------------------------------------------------------------------------
    if (form) {
        form.addEventListener('submit', (e) => {
            let isValid = true;
            const requiredInputs = form.querySelectorAll('input[required], select[required]');

            requiredInputs.forEach((input) => {
                const group = input.closest('.form-group');
                // Remove any previous error message
                const existingError = group.querySelector('.error-message');
                if (existingError) {
                    existingError.remove();
                }
                group.classList.remove('has-error');

                if (!input.value.trim() && input.type !== 'file') {
                    isValid = false;
                    showFieldError(group, 'This field is required.');
                } else if (input.type === 'file' && (!input.files || input.files.length === 0)) {
                    isValid = false;
                    showFieldError(group, 'Please select a student photo.');
                } else if (input.type === 'email' && input.value.trim()) {
                    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                    if (!emailRegex.test(input.value.trim())) {
                        isValid = false;
                        showFieldError(group, 'Please enter a valid email address.');
                    }
                }
            });

            if (!isValid) {
                e.preventDefault();
            }
        });

        // Clear error styles on user interaction
        form.querySelectorAll('input, select').forEach((element) => {
            element.addEventListener('input', () => {
                const group = element.closest('.form-group');
                if (group && group.classList.contains('has-error')) {
                    group.classList.remove('has-error');
                    const err = group.querySelector('.error-message');
                    if (err) err.remove();
                }
            });
        });
    }

    function showFieldError(group, message) {
        group.classList.add('has-error');
        const errorEl = document.createElement('span');
        errorEl.className = 'error-message';
        errorEl.textContent = message;
        group.appendChild(errorEl);
    }
});
