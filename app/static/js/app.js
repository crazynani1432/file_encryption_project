// Global Toast Notification Helper
function showToast(title, message, type = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    
    let icon = "ℹ️";
    if (type === "success") icon = "✅";
    if (type === "error") icon = "❌";

    toast.innerHTML = `
        <span class="toast-icon">${icon}</span>
        <div class="toast-body">
            <div class="toast-title">${title}</div>
            <div class="toast-msg">${message}</div>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">×</button>
    `;

    container.appendChild(toast);

    // Auto dismiss after 4.5 seconds
    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateX(50px)";
        setTimeout(() => toast.remove(), 300);
    }, 4500);
}

// Toggle password input visibility (Show/Hide password)
function togglePasswordVisibility(inputId, btn) {
    const input = document.getElementById(inputId);
    if (!input) return;
    if (input.type === "password") {
        input.type = "text";
        btn.textContent = "🙈";
    } else {
        input.type = "password";
        btn.textContent = "👁️";
    }
}

// Add extra email row to recipient email container
function addEmailInputRow() {
    const container = document.getElementById("recipient-emails-container");
    if (!container) return;
    
    const row = document.createElement("div");
    row.className = "input-wrapper email-input-row";
    row.innerHTML = `
        <span class="input-icon">✉️</span>
        <input type="email" class="policy-otp-email-field" placeholder="e.g., recipient@domain.com" style="padding-right: 42px;" required>
        <button type="button" class="remove-email-btn" onclick="this.parentElement.remove()">❌</button>
    `;
    container.appendChild(row);
}

// Authentication Forms Toggle (index.html)
function switchTab(tab) {
    const tabLogin = document.getElementById("tab-login");
    const tabRegister = document.getElementById("tab-register");
    const formLogin = document.getElementById("form-login");
    const formRegister = document.getElementById("form-register");

    if (tab === "login") {
        tabLogin.classList.add("active");
        tabRegister.classList.remove("active");
        formLogin.classList.remove("hidden");
        formRegister.classList.add("hidden");
    } else {
        tabLogin.classList.remove("active");
        tabRegister.classList.add("active");
        formLogin.classList.add("hidden");
        formRegister.classList.remove("hidden");
    }
}

// Login Handler
async function handleLogin(event) {
    event.preventDefault();
    const btn = document.getElementById("btn-login-submit");
    const spinner = btn.querySelector(".spinner");
    const btnText = btn.querySelector(".btn-text");

    const usernameOrEmail = document.getElementById("login-username").value;
    const password = document.getElementById("login-password").value;

    // Toggle loader UI
    spinner.classList.remove("hidden");
    btnText.textContent = "Authenticating...";
    btn.disabled = true;

    const formData = new FormData();
    formData.append("username_or_email", usernameOrEmail);
    formData.append("password", password);

    try {
        const response = await fetch("/api/auth/login", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            showToast("Authenticated", `Welcome back, ${data.username}! Connecting session...`, "success");
            setTimeout(() => {
                window.location.href = "/dashboard";
            }, 1000);
        } else {
            showToast("Access Denied", data.detail || "Invalid credentials", "error");
            spinner.classList.add("hidden");
            btnText.textContent = "Authenticate";
            btn.disabled = false;
        }
    } catch (err) {
        showToast("Connection Error", "Could not reach authorization server.", "error");
        spinner.classList.add("hidden");
        btnText.textContent = "Authenticate";
        btn.disabled = false;
    }
}

// Register Handler
async function handleRegister(event) {
    event.preventDefault();
    const btn = document.getElementById("btn-reg-submit");
    const spinner = btn.querySelector(".spinner");
    const btnText = btn.querySelector(".btn-text");

    const username = document.getElementById("reg-username").value;
    const email = document.getElementById("reg-email").value;
    const password = document.getElementById("reg-password").value;

    spinner.classList.remove("hidden");
    btnText.textContent = "Registering Node...";
    btn.disabled = true;

    const formData = new FormData();
    formData.append("username", username);
    formData.append("email", email);
    formData.append("password", password);

    try {
        const response = await fetch("/api/auth/register", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            showToast("Registration Success", "Account created successfully. You can now log in.", "success");
            event.target.reset();
            switchTab("login");
        } else {
            showToast("Registration Failed", data.detail || "Check input details", "error");
        }
    } catch (err) {
        showToast("Connection Error", "Unable to complete server registration.", "error");
    } finally {
        spinner.classList.add("hidden");
        btnText.textContent = "Register Account";
        btn.disabled = false;
    }
}

// Logout Handler
async function handleLogout() {
    try {
        const response = await fetch("/api/auth/logout", { method: "POST" });
        if (response.ok) {
            window.location.href = "/";
        } else {
            showToast("Logout Error", "Failed to clear authentication token.", "error");
        }
    } catch (err) {
        window.location.href = "/";
    }
}

// Access Policy Selector (dashboard.html)
function selectPolicy(policy) {
    // Reset active visual states
    document.getElementById("policy-lbl-pwd").classList.remove("active");
    document.getElementById("policy-lbl-q").classList.remove("active");
    document.getElementById("policy-lbl-otp").classList.remove("active");

    // Hide input parameters sections
    document.getElementById("policy-params-password").classList.add("hidden");
    document.getElementById("policy-params-question").classList.add("hidden");
    document.getElementById("policy-params-otp").classList.add("hidden");

    // Apply selected configurations
    if (policy === "PASSWORD") {
        document.getElementById("policy-lbl-pwd").classList.add("active");
        document.getElementById("policy-params-password").classList.remove("hidden");
        document.getElementById("policy-pwd-input").required = true;
        document.getElementById("policy-q-input").required = false;
        document.getElementById("policy-a-input").required = false;
        const firstEmail = document.querySelector(".policy-otp-email-field");
        if (firstEmail) firstEmail.required = false;
    } else if (policy === "QUESTION") {
        document.getElementById("policy-lbl-q").classList.add("active");
        document.getElementById("policy-params-question").classList.remove("hidden");
        document.getElementById("policy-pwd-input").required = false;
        document.getElementById("policy-q-input").required = true;
        document.getElementById("policy-a-input").required = true;
        const firstEmail = document.querySelector(".policy-otp-email-field");
        if (firstEmail) firstEmail.required = false;
    } else if (policy === "OTP") {
        document.getElementById("policy-lbl-otp").classList.add("active");
        document.getElementById("policy-params-otp").classList.remove("hidden");
        document.getElementById("policy-pwd-input").required = false;
        document.getElementById("policy-q-input").required = false;
        document.getElementById("policy-a-input").required = false;
        const firstEmail = document.querySelector(".policy-otp-email-field");
        if (firstEmail) firstEmail.required = true;
    }

    // Set correct radio value
    const radios = document.getElementsByName("access_policy");
    for (let r of radios) {
        if (r.value === policy) {
            r.checked = true;
            break;
        }
    }
}

// Selected File Label (dashboard.html drag zone)
function updateSelectedFileLabel() {
    const fileInput = document.getElementById("upload-file");
    const nameLabel = document.getElementById("selected-file-name");
    
    if (fileInput.files.length > 0) {
        nameLabel.textContent = `Selected: ${fileInput.files[0].name}`;
        nameLabel.classList.remove("hidden");
    } else {
        nameLabel.classList.add("hidden");
    }
}

// Load Files List Table
async function loadDashboardData() {
    const tableBody = document.getElementById("files-list-body");
    const noFilesState = document.getElementById("no-files-state");
    if (!tableBody) return; // Prevent run if not on dashboard page

    try {
        const response = await fetch("/api/files/my-files");
        if (response.status === 401) {
            window.location.href = "/";
            return;
        }
        
        const files = await response.json();
        tableBody.innerHTML = "";

        if (files.length === 0) {
            noFilesState.classList.remove("hidden");
            return;
        }

        noFilesState.classList.add("hidden");

        files.forEach(f => {
            const dateStr = new Date(f.created_at).toLocaleString();
            
            // Format dynamic policy details column
            let detail = "—";
            if (f.access_policy === "PASSWORD") {
                detail = "🔑 Encrypted Symmetric Key";
            } else if (f.access_policy === "QUESTION") {
                detail = `❓ Q: "${f.security_question}"`;
            } else if (f.access_policy === "OTP") {
                // Obfuscate recipient emails list for display
                const p = f.recipient_email;
                let masked = p;
                if (p) {
                    masked = p.split(",").map(email => {
                        const trimmed = email.trim();
                        if (trimmed.includes("@")) {
                            const parts = trimmed.split("@");
                            const name = parts[0];
                            const domain = parts[1];
                            const nameMask = name.length > 2 ? `${name.slice(0, 2)}***` : "***";
                            return `${nameMask}@${domain}`;
                        }
                        return trimmed;
                    }).join(", ");
                }
                detail = `✉️ Email to: ${masked}`;
            }

            const gmailBtn = f.access_policy === "OTP"
                ? `<button class="btn btn-gmail btn-sm" id="btn-gmail-${f.id}" onclick="sendViaGmail('${f.id}', this)" title="Send share link to recipient Gmail inbox">📧 Send via Gmail</button>`
                : "";

            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>${escapeHTML(f.filename)}</strong></td>
                <td><span class="badge-policy ${f.access_policy}">${f.access_policy}</span></td>
                <td><span class="helper-text" title="${escapeHTML(detail)}">${escapeHTML(detail)}</span></td>
                <td>${dateStr}</td>
                <td>
                    <div class="file-row-actions">
                        <button class="btn btn-secondary btn-sm" onclick="copyShareLink('${f.id}')">Copy Link</button>
                        ${gmailBtn}
                        <button class="btn btn-secondary btn-sm btn-danger-hover" onclick="deleteFile('${f.id}')">Delete</button>
                    </div>
                </td>
            `;
            tableBody.appendChild(tr);
        });
    } catch (err) {
        showToast("Error loading files", "Unable to pull file records from database.", "error");
    }
}

// File Upload Handler
async function handleFileUpload(event) {
    event.preventDefault();
    const btn = document.getElementById("btn-upload-submit");
    const spinner = btn.querySelector(".spinner");
    const btnText = btn.querySelector(".btn-text");

    const fileInput = document.getElementById("upload-file");
    const policyRadios = document.getElementsByName("access_policy");
    
    let activePolicy = "PASSWORD";
    for (let r of policyRadios) {
        if (r.checked) {
            activePolicy = r.value;
            break;
        }
    }

    if (fileInput.files.length === 0) {
        showToast("Input Error", "Please select a file to encrypt.", "error");
        return;
    }

    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append("file", file);
    formData.append("access_policy", activePolicy);

    if (activePolicy === "PASSWORD") {
        const pwd = document.getElementById("policy-pwd-input").value;
        formData.append("password", pwd);
    } else if (activePolicy === "QUESTION") {
        const q = document.getElementById("policy-q-input").value;
        const a = document.getElementById("policy-a-input").value;
        formData.append("security_question", q);
        formData.append("security_answer", a);
    } else if (activePolicy === "OTP") {
        const emailFields = document.querySelectorAll(".policy-otp-email-field");
        const emails = [];
        emailFields.forEach(el => {
            const val = el.value.trim();
            if (val) emails.push(val);
        });
        if (emails.length === 0) {
            showToast("Input Error", "Please provide at least one recipient email address.", "error");
            return;
        }
        formData.append("recipient_email", emails.join(","));
    }

    // Loader configuration
    spinner.classList.remove("hidden");
    btnText.textContent = "Locking & Encrypting...";
    btn.disabled = true;

    try {
        const response = await fetch("/api/files/upload", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            showToast("Encrypted Successful", `File "${data.filename}" encrypted with ${activePolicy} policy.`, "success");
            event.target.reset();
            updateSelectedFileLabel();
            // Default to Password policy input
            selectPolicy("PASSWORD");
            // Reload table
            await loadDashboardData();
        } else {
            showToast("Upload Failed", data.detail || "Server failed to process file", "error");
        }
    } catch (err) {
        showToast("Error", "Could not complete upload request.", "error");
    } finally {
        spinner.classList.add("hidden");
        btnText.textContent = "Lock & Encrypt File";
        btn.disabled = false;
    }
}

// Copy sharing download URL to clipboard
function copyShareLink(fileId) {
    const url = window.location.origin + "/share/" + fileId;
    navigator.clipboard.writeText(url).then(() => {
        showToast("Copied Link", "Public share URL copied to clipboard.", "success");
    }).catch(err => {
        showToast("Clipboard Error", `URL: ${url}`, "info");
    });
}

// Delete file handler
async function deleteFile(fileId) {
    if (!confirm("Are you sure you want to delete this file? This will wipe the encrypted ciphertext from backend storage permanently.")) {
        return;
    }

    try {
        const response = await fetch(`/api/files/delete/${fileId}`, {
            method: "DELETE"
        });
        const data = await response.json();
        
        if (response.ok) {
            showToast("Deleted", "Secure file container wiped successfully.", "success");
            loadDashboardData();
        } else {
            showToast("Delete Failed", data.detail || "Server rejected deletion", "error");
        }
    } catch (err) {
        showToast("Error", "Could not complete request.", "error");
    }
}

// Send share link to recipient's Gmail inbox via admin Gmail (OTP files only)
async function sendViaGmail(fileId, btnEl) {
    if (!btnEl) return;
    const originalText = btnEl.innerHTML;
    btnEl.disabled = true;
    btnEl.innerHTML = "⏳ Sending...";

    try {
        const response = await fetch(`/api/files/send-link/${fileId}`, {
            method: "POST"
        });
        const data = await response.json();

        if (response.ok) {
            showToast("📧 Email Sent!", data.message || "Share link dispatched to recipient Gmail inbox.", "success");
            btnEl.innerHTML = "✅ Sent!";
            setTimeout(() => {
                btnEl.innerHTML = originalText;
                btnEl.disabled = false;
            }, 4000);
        } else {
            showToast("Send Failed", data.detail || "Unable to send email.", "error");
            btnEl.innerHTML = originalText;
            btnEl.disabled = false;
        }
    } catch (err) {
        showToast("Connection Error", "Could not contact email dispatch server.", "error");
        btnEl.innerHTML = originalText;
        btnEl.disabled = false;
    }
}

// Request OTP dispatch for public downloads (decrypt.html)
async function requestOTP(fileId) {
    const btn = document.getElementById("btn-request-otp");
    if (!btn) return;

    const emailInput = document.getElementById("challenge-otp-email");
    if (!emailInput || !emailInput.value.trim() || !emailInput.checkValidity()) {
        showToast("Input Error", "Please enter a valid authorized email address to request OTP.", "error");
        return;
    }
    const email = emailInput.value.trim();

    btn.disabled = true;
    btn.textContent = "Dispatching OTP...";

    const formData = new FormData();
    formData.append("email", email);

    try {
        const response = await fetch(`/api/files/share/${fileId}/request-otp`, {
            method: "POST",
            body: formData
        });
        const data = await response.json();

        if (response.ok) {
            showToast("OTP Sent", "A new verification code was sent to the designated email address.", "success");
            // Reveal input code challenge
            document.getElementById("form-decrypt-challenge").classList.remove("hidden");
            
            // Disable email input during verification
            emailInput.disabled = true;
            
            // Countdown cooldown timer (30 seconds)
            let cooldown = 30;
            const timer = setInterval(() => {
                cooldown--;
                if (cooldown <= 0) {
                    clearInterval(timer);
                    btn.disabled = false;
                    btn.textContent = "Request Verification OTP";
                    emailInput.disabled = false;
                } else {
                    btn.textContent = `Resend available in ${cooldown}s`;
                }
            }, 1000);
        } else {
            showToast("OTP Request Failed", data.detail || "Unable to send verification email", "error");
            btn.disabled = false;
            btn.textContent = "Request Verification OTP";
        }
    } catch (err) {
        showToast("Connection Error", "Failed to dispatch email request.", "error");
        btn.disabled = false;
        btn.textContent = "Request Verification OTP";
    }
}

// Submit recipient challenge answer/password/OTP for verification & download
async function handleChallengeSubmit(event, policy) {
    event.preventDefault();
    const submitBtn = document.getElementById("btn-decrypt-submit");
    const challengeForm = document.getElementById("form-decrypt-challenge");
    const statusScreen = document.getElementById("decrypt-status-screen");

    // Extract file UUID from current path /share/{uuid}
    const pathParts = window.location.pathname.split("/");
    const fileId = pathParts[pathParts.length - 1];

    const formData = new FormData();

    if (policy === "PASSWORD") {
        const pwd = document.getElementById("challenge-password").value;
        formData.append("password", pwd);
    } else if (policy === "QUESTION") {
        const ans = document.getElementById("challenge-answer").value;
        formData.append("security_answer", ans);
    } else if (policy === "OTP") {
        const otp = document.getElementById("challenge-otp").value;
        const email = document.getElementById("challenge-otp-email").value.trim();
        formData.append("otp_code", otp);
        formData.append("email", email);
    }

    // Toggle loader screen state
    if (challengeForm) challengeForm.classList.add("hidden");
    if (statusScreen) statusScreen.classList.remove("hidden");

    try {
        const response = await fetch(`/api/files/share/${fileId}/verify-challenge`, {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            showToast("Challenge Verified", "Starting secure streaming download...", "success");
            
            // Trigger direct stream download using temporary verification token
            const token = data.download_token;
            window.location.href = `/api/files/share/${fileId}/download?token=${token}`;
            
            // Keep loader active for 4 seconds then return back to challenge (in case they need to download again)
            setTimeout(() => {
                if (statusScreen) statusScreen.classList.add("hidden");
                if (challengeForm) challengeForm.classList.remove("hidden");
            }, 4000);
        } else {
            showToast("Verification Failed", data.detail || "Authentication challenge was incorrect.", "error");
            if (statusScreen) statusScreen.classList.add("hidden");
            if (challengeForm) challengeForm.classList.remove("hidden");
        }
    } catch (err) {
        showToast("Error", "Could not contact streaming server.", "error");
        if (statusScreen) statusScreen.classList.add("hidden");
        if (challengeForm) challengeForm.classList.remove("hidden");
    }
}

// HTML XSS Sanitization Helper
function escapeHTML(str) {
    if (!str) return "";
    return str.replace(/[&<>'"]/g, 
        tag => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[tag] || tag)
    );
}

// Drag & Drop event bindings
document.addEventListener("DOMContentLoaded", () => {
    const dragZone = document.getElementById("drag-zone");
    const fileInput = document.getElementById("upload-file");
    if (dragZone && fileInput) {
        dragZone.addEventListener("click", () => fileInput.click());
        
        dragZone.addEventListener("dragover", (e) => {
            e.preventDefault();
            dragZone.classList.add("dragover");
        });

        dragZone.addEventListener("dragleave", () => {
            dragZone.classList.remove("dragover");
        });

        dragZone.addEventListener("drop", (e) => {
            e.preventDefault();
            dragZone.classList.remove("dragover");
            if (e.dataTransfer.files.length > 0) {
                fileInput.files = e.dataTransfer.files;
                updateSelectedFileLabel();
            }
        });
    }
});
