const video = document.getElementById('video');
const canvas = document.getElementById('canvas');

const captureBtn = document.getElementById('captureBtn');
const uploadScanBtn = document.getElementById('uploadScanBtn');

const uploadInput = document.getElementById('uploadInput');
const uploadPreview = document.getElementById('uploadPreview');

const inputMode = document.getElementById('inputMode');

const scanTypeSelect = document.getElementById('scanType');

const attendanceFields = document.getElementById('attendanceFields');
const visitorFields = document.getElementById('visitorFields');

const classCodeInput = document.getElementById('classCode');
const hostEmailInput = document.getElementById('hostEmail');
const organizationInput = document.getElementById('organization');

const extractedDiv = document.getElementById('extractedData');
const confirmBtn = document.getElementById('confirmBtn');
const ocrProgress = document.getElementById('ocrProgress');

let stream = null;
let extractedData = null;
let uploadedBase64 = null;

async function initCamera() {

    try {
        stream = await navigator.mediaDevices.getUserMedia({
            video: { width: 640, height: 480, facingMode: "environment" },
            audio: false
        });

        video.srcObject = stream;
        await video.play();

        console.log("Camera started");

    } catch (err) {
        console.error(err);
        alert("Camera error: " + err.message);
    }
}

inputMode.addEventListener('change', async function () {

    const mode = this.value;

    if (mode === 'camera') {

        uploadInput.value = '';
        uploadPreview.innerHTML = '';
        uploadedBase64 = null;

        uploadScanBtn.disabled = true;

        document.getElementById('uploadContainer').style.display = 'none';
        document.getElementById('cameraContainer').style.display = 'block';

        await initCamera();

    } else {

        document.getElementById('cameraContainer').style.display = 'none';
        document.getElementById('uploadContainer').style.display = 'block';

        if (stream) {
            stream.getTracks().forEach(t => t.stop());
            stream = null;
        }
    }
});

function captureImage() {

    const ctx = canvas.getContext('2d');

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    return canvas.toDataURL('image/jpeg', 0.9)
        .split(',')[1];
}

async function sendOCR(imageBase64) {

    if (!imageBase64) {
        console.error("No image provided");
        return;
    }

    ocrProgress.style.display = 'block';

    const form = new FormData();

    const type = scanTypeSelect.value;

    form.append('image_base64', imageBase64);
    form.append('id_type', type === 'attendance' ? 'student' : 'auto');
    form.append('action', 'extract');
    form.append('engine', 'easyocr');

    if (type === 'attendance') {
        form.append('class_code', classCodeInput.value.trim());
    }

    if (type === 'visitor') {
        form.append('host_email', hostEmailInput.value.trim());
        form.append('organization', organizationInput.value.trim());
    }

    try {

        const res = await fetch('/api/v1/ocr/process/', {
            method: 'POST',
            headers: { 'X-CSRFToken': csrfToken },
            body: form
        });

        const data = await res.json();

        console.log("OCR RESPONSE:", data);

        if (data.success) {

            extractedData = data.extracted_data;

            displayExtractedData(extractedData);

            confirmBtn.disabled = false;

        } else {
            alert(data.error || "OCR failed");
        }

    } catch (err) {
        console.error(err);
        alert("OCR request failed");

    } finally {
        ocrProgress.style.display = 'none';
    }
}

captureBtn.addEventListener('click', async () => {

    const img = captureImage();

    if (!img) {
        alert("Camera not ready");
        return;
    }

    await sendOCR(img);
});

uploadScanBtn.addEventListener('click', async () => {

    if (!uploadedBase64) {
        alert("Select an image first");
        return;
    }

    await sendOCR(uploadedBase64);
});

uploadInput.addEventListener('change', function (e) {

    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();

    reader.onload = function (event) {

        uploadedBase64 = event.target.result.split(',')[1];

        uploadPreview.style.display = 'block';

        uploadPreview.innerHTML = `
            <img src="${event.target.result}"
                 style="max-width:100%;
                        border-radius:10px;
                        border:1px solid #ddd;" />
        `;

        // ONLY enable button — DO NOT RUN OCR HERE
        uploadScanBtn.disabled = false;
    };

    reader.readAsDataURL(file);
});

uploadScanBtn.addEventListener('click', async function () {

    if (!uploadedBase64) {
        alert("Please select an image first.");
        return;
    }

    this.disabled = true;
    this.innerHTML = '<i class="bx bx-loader-alt bx-spin"></i> Processing...';

    try {

        //  SAME PIPELINE AS CAMERA
        await sendOCR(uploadedBase64);

        // optional: reset button state after success
        this.innerHTML = '<i class="bx bx-upload"></i> Process Upload';

    } catch (err) {

        console.error(err);
        alert("Upload OCR failed");

    } finally {

        this.disabled = false;
    }
});