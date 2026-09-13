// DOM Elements
const loginSection = document.getElementById("loginSection");
const registerSection = document.getElementById("registerSection");
const twoFactorSection = document.getElementById("twoFactorSection");
const dashboardSection = document.getElementById("dashboardSection");
const authCard = document.querySelector(".auth-card");
const forgotPasswordSection = document.getElementById("forgotPasswordSection");
const resetPasswordSection = document.getElementById("resetPasswordSection");

const loginForm = document.getElementById("loginForm");
const registerForm = document.getElementById("registerForm");
const twoFactorForm = document.getElementById("twoFactorForm");
const confirmTwoFactorForm = document.getElementById("confirmTwoFactorForm");
const disableTwoFactorForm = document.getElementById("disableTwoFactorForm");
const forgotPasswordForm = document.getElementById("forgotPasswordForm");
const resetPasswordForm = document.getElementById("resetPasswordForm");
const offerTutoringForm = document.getElementById("offerTutoringForm");

const loginMessage = document.getElementById("loginMessage");
const registerMessage = document.getElementById("registerMessage");
const twoFactorMessage = document.getElementById("twoFactorMessage");
const setupTwoFactorMessage = document.getElementById("setupTwoFactorMessage");
const disableTwoFactorMessage = document.getElementById("disableTwoFactorMessage");
const forgotPasswordMessage = document.getElementById("forgotPasswordMessage");
const resetPasswordMessage = document.getElementById("resetPasswordMessage");
const offerTutoringMessage = document.getElementById("offerTutoringMessage");

const showRegister = document.getElementById("showRegister");
const showLogin = document.getElementById("showLogin");
const backToLogin = document.getElementById("backToLogin");
const logoutBtn = document.getElementById("logoutBtn");
const showForgotPassword = document.getElementById("showForgotPassword");
const backToLoginFromForgotPassword = document.getElementById("backToLoginFromForgotPassword");
const dashboardNavigation = document.getElementById("dashboardNavigation");
const enrollmentConfirmationModal = document.getElementById("enrollmentConfirmationModal");
const enrollmentConfirmationTitle = document.getElementById("enrollmentConfirmationTitle");
const enrollmentConfirmationMessage = document.getElementById("enrollmentConfirmationMessage");
const confirmEnrollmentAction = document.getElementById("confirmEnrollmentAction");

let currentUser = null;
let pendingTwoFactorSecret = null;
let pendingEnrollmentAction = null;
const enrollmentModal = new bootstrap.Modal(enrollmentConfirmationModal);

// SEÇÃO DE NAVEGAÇÃO

showRegister.addEventListener("click", () => {
    loginSection.classList.add("d-none");
    registerSection.classList.remove("d-none");
    loginMessage.innerHTML = "";
});

showForgotPassword.addEventListener("click", () => {
    loginSection.classList.add("d-none");
    forgotPasswordSection.classList.remove("d-none");
    loginMessage.innerHTML = "";
});

showLogin.addEventListener("click", () => {
    registerSection.classList.add("d-none");
    loginSection.classList.remove("d-none");
    registerMessage.innerHTML = "";
});

backToLoginFromForgotPassword.addEventListener("click", () => {
    forgotPasswordSection.classList.add("d-none");
    loginSection.classList.remove("d-none");
    forgotPasswordMessage.innerHTML = "";
    forgotPasswordForm.reset();
});

backToLogin.addEventListener("click", () => {
    twoFactorSection.classList.add("d-none");
    loginSection.classList.remove("d-none");
    twoFactorMessage.innerHTML = "";
    document.getElementById("twoFactorCode").value = "";
});

logoutBtn.addEventListener("click", async () => {
    // 1. Avisa o backend para destruir a sessão no banco e limpar o cookie
    try {
        await fetch("/auth/logout", { method: "POST" });
    } catch (error) {
        console.error("Erro ao fazer logout no servidor:", error);
    }

    // 2. Limpa o estado no frontend e volta pra tela de login
    currentUser = null;
    authCard.classList.remove("dashboard-active");
    dashboardSection.classList.add("d-none");
    loginSection.classList.remove("d-none");
    loginForm.reset();
    loginMessage.innerHTML = "";
    showDashboardScreen("overviewScreen");
});

function showDashboardScreen(screenId) {
    document.querySelectorAll(".dashboard-screen").forEach((screen) => {
        screen.classList.toggle("d-none", screen.id !== screenId);
    });

    dashboardNavigation.querySelectorAll("[data-dashboard-screen]").forEach((button) => {
        button.classList.toggle("active", button.dataset.dashboardScreen === screenId);
    });
}

dashboardSection.addEventListener("click", (event) => {
    const navigationButton = event.target.closest("[data-dashboard-screen]");
    if (navigationButton) {
        showDashboardScreen(navigationButton.dataset.dashboardScreen);
    }
});

function renderTutoringCard(tutoringOffer, action = "") {
    const actionButton = action === "enroll"
        ? `<button class="btn btn-primary btn-sm tutoring-action enroll-tutoring"
                data-tutoring-offer-id="${tutoringOffer.id}">
                <span class="me-1">+</span> Inscrever-se
           </button>`
        : action === "unsubscribe"
            ? `<button class="btn btn-outline-danger btn-sm tutoring-action unsubscribe-tutoring"
                data-tutoring-offer-id="${tutoringOffer.id}">
                Desinscrever-se
               </button>`
            : "";

    return `
        <div class="col-md-6">
            <div class="card border-0 shadow-sm h-100">
                <div class="card-body">
                    <h6 class="card-title">${tutoringOffer.disciplina}</h6>
                    <p class="card-text mb-3">${tutoringOffer.descricao}</p>
                    <div class="d-flex justify-content-between align-items-center gap-2">
                        <small class="text-muted text-truncate">Monitor: ${tutoringOffer.monitor.full_name}</small>
                        ${actionButton}
                    </div>
                </div>
            </div>
        </div>
    `;
}

function renderEmptyMessage(message) {
    return `<p class="text-muted">${message}</p>`;
}

async function loadTutoringOffers() {
    const availableContainer = document.getElementById("availableTutoringOffers");
    const offeredContainer = document.getElementById("offeredTutoringOffers");
    const enrolledContainer = document.getElementById("enrolledTutoringOffers");

    try {
        const [availableResponse, mineResponse] = await Promise.all([
            fetch("/tutoring-offers"),
            fetch("/tutoring-offers/mine")
        ]);
        const availableData = await availableResponse.json();
        const mineData = await mineResponse.json();

        if (!availableResponse.ok || !mineResponse.ok) {
            throw new Error(availableData.error || mineData.error);
        }

        availableContainer.innerHTML = availableData.monitorias.length
            ? availableData.monitorias.map(item => renderTutoringCard(item, "enroll")).join("")
            : renderEmptyMessage("Nenhuma monitoria disponível no momento.");
        offeredContainer.innerHTML = mineData.oferecidas.length
            ? mineData.oferecidas.map(item => renderTutoringCard(item)).join("")
            : renderEmptyMessage("Você ainda não ofereceu uma monitoria.");
        enrolledContainer.innerHTML = mineData.inscricoes.length
            ? mineData.inscricoes.map(item => renderTutoringCard(item.monitoria, "unsubscribe")).join("")
            : renderEmptyMessage("Você ainda não está inscrito em uma monitoria.");
    } catch (error) {
        availableContainer.innerHTML = `
            <div class="alert alert-danger">Não foi possível carregar as monitorias.</div>
        `;
    }
}

offerTutoringForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    offerTutoringMessage.innerHTML = "";

    try {
        const response = await fetch("/tutoring-offers", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                disciplina: document.getElementById("tutoringSubject").value,
                descricao: document.getElementById("tutoringDescription").value
            })
        });
        const data = await response.json();

        if (!response.ok) {
            offerTutoringMessage.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
            return;
        }

        offerTutoringMessage.innerHTML = `<div class="alert alert-success">${data.message}</div>`;
        offerTutoringForm.reset();
        loadTutoringOffers();
    } catch (error) {
        offerTutoringMessage.innerHTML = `
            <div class="alert alert-danger">Não foi possível conectar ao servidor.</div>
        `;
    }
});

function openEnrollmentConfirmation(action, tutoringOfferId) {
    pendingEnrollmentAction = { action, tutoringOfferId };
    const isEnrollment = action === "enroll";

    enrollmentConfirmationTitle.textContent = isEnrollment
        ? "Confirmar inscrição"
        : "Confirmar desinscrição";
    enrollmentConfirmationMessage.textContent = isEnrollment
        ? "Deseja se inscrever nesta monitoria?"
        : "Deseja cancelar sua inscrição nesta monitoria?";
    confirmEnrollmentAction.textContent = isEnrollment ? "Inscrever-se" : "Desinscrever-se";
    confirmEnrollmentAction.className = isEnrollment
        ? "btn btn-primary"
        : "btn btn-danger";
    enrollmentModal.show();
}

async function executeEnrollmentAction() {
    if (!pendingEnrollmentAction) {
        return;
    }

    const { action, tutoringOfferId } = pendingEnrollmentAction;
    const isEnrollment = action === "enroll";
    confirmEnrollmentAction.disabled = true;

    try {
        const response = await fetch(
            isEnrollment
                ? `/tutoring-offers/${tutoringOfferId}/enrollments`
                : `/tutoring-offers/${tutoringOfferId}/enrollment`,
            { method: isEnrollment ? "POST" : "DELETE" }
        );
        const data = await response.json();

        if (!response.ok) {
            enrollmentConfirmationMessage.innerHTML =
                `<div class="alert alert-danger mb-0">${data.error}</div>`;
            return;
        }

        enrollmentModal.hide();
        loadTutoringOffers();
    } catch (error) {
        enrollmentConfirmationMessage.innerHTML =
            '<div class="alert alert-danger mb-0">Não foi possível conectar ao servidor.</div>';
    } finally {
        confirmEnrollmentAction.disabled = false;
        pendingEnrollmentAction = null;
    }
}

confirmEnrollmentAction.addEventListener("click", executeEnrollmentAction);

document.getElementById("availableTutoringOffers").addEventListener("click", (event) => {
    const button = event.target.closest(".enroll-tutoring");
    if (!button) {
        return;
    }

    openEnrollmentConfirmation("enroll", button.dataset.tutoringOfferId);
});

document.getElementById("enrolledTutoringOffers").addEventListener("click", (event) => {
    const button = event.target.closest(".unsubscribe-tutoring");
    if (!button) {
        return;
    }

    openEnrollmentConfirmation("unsubscribe", button.dataset.tutoringOfferId);
});

// CADASTRO

registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    registerMessage.innerHTML = "";

    const fullName = document.getElementById("registerFullName").value;
    const username = document.getElementById("registerUsername").value;
    const email = document.getElementById("registerEmail").value;
    const password = document.getElementById("registerPassword").value;

    try {
        const response = await fetch("/auth/register", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                full_name: fullName,
                username,
                email,
                password
            })
        });

        const data = await response.json();

        if (!response.ok) {
            registerMessage.innerHTML = `
                <div class="alert alert-danger">
                    ${data.error}
                </div>
            `;
            return;
        }

        registerMessage.innerHTML = `
            <div class="alert alert-success">
                ${data.message}
            </div>
        `;

        registerForm.reset();

    } catch (error) {
        registerMessage.innerHTML = `
            <div class="alert alert-danger">
                Não foi possível conectar ao servidor.
            </div>
        `;
    }
});

// RECUPERAÇÃO DE SENHA

forgotPasswordForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    forgotPasswordMessage.innerHTML = "";

    const email = document.getElementById("forgotPasswordEmail").value;

    try {
        const response = await fetch("/auth/forgot-password", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                email
            })
        });

        const data = await response.json();

        if (!response.ok) {
            forgotPasswordMessage.innerHTML = `
                <div class="alert alert-danger">
                    ${data.error}
                </div>
            `;
            return;
        }

        forgotPasswordMessage.innerHTML = `
            <div class="alert alert-success">
                ${data.message}
            </div>
        `;

        forgotPasswordForm.reset();

    } catch (error) {
        forgotPasswordMessage.innerHTML = `
            <div class="alert alert-danger">
                Não foi possível conectar ao servidor.
            </div>
        `;
    }
});

// REDEFINIÇÃO DE SENHA

resetPasswordForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    resetPasswordMessage.innerHTML = "";

    const newPassword = document.getElementById("resetPassword").value;
    const confirmPassword = document.getElementById("resetPasswordConfirm").value;

    // Verifica se as senhas são iguais.
    if (newPassword !== confirmPassword) {
        resetPasswordMessage.innerHTML = `
            <div class="alert alert-danger">
                As senhas não coincidem.
            </div>
        `;
        return;
    }

    // Recupera o token enviado no link do e-mail.
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get("token");

    if (!token) {
        resetPasswordMessage.innerHTML = `
            <div class="alert alert-danger">
                Link de recuperação inválido.
            </div>
        `;
        return;
    }

    try {
        const response = await fetch("/auth/reset-password", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                token,
                new_password: newPassword
            })
        });

        const data = await response.json();

        if (!response.ok) {
            resetPasswordMessage.innerHTML = `
                <div class="alert alert-danger">
                    ${data.error}
                </div>
            `;
            return;
        }

        resetPasswordMessage.innerHTML = `
            <div class="alert alert-success">
                ${data.message}
            </div>
        `;

        resetPasswordForm.reset();

        // Remove o token da URL.
        window.history.replaceState({}, document.title, "/");

        // Depois de 2 segundos, volta para o login.
        setTimeout(() => {
            resetPasswordSection.classList.add("d-none");
            loginSection.classList.remove("d-none");
            resetPasswordMessage.innerHTML = "";
        }, 2000);

    } catch (error) {
        resetPasswordMessage.innerHTML = `
            <div class="alert alert-danger">
                Não foi possível conectar ao servidor.
            </div>
        `;
    }
});

// LOGIN

loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    loginMessage.innerHTML = "";

    const email = document.getElementById("loginEmail").value;
    const password = document.getElementById("loginPassword").value;

    try {
        const response = await fetch("/auth/login", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                email,
                password
            })
        });

        const data = await response.json();

        if (!response.ok) {
            loginMessage.innerHTML = `
                <div class="alert alert-danger">
                    ${data.error}
                </div>
            `;
            return;
        }

        // Se requer 2FA, mostrar tela de verificação
        if (data.requires_2fa) {
            loginSection.classList.add("d-none");
            twoFactorSection.classList.remove("d-none");
            return;
        }

        // Caso contrário, login bem-sucedido
        currentUser = data.user;
        authCard.classList.add("dashboard-active");
        showDashboard();

    } catch (error) {
        loginMessage.innerHTML = `
            <div class="alert alert-danger">
                Não foi possível conectar ao servidor.
            </div>
        `;
    }
});

// VERIFICAÇÃO 2FA

twoFactorForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    twoFactorMessage.innerHTML = "";

    const code = document.getElementById("twoFactorCode").value;

    try {
        const response = await fetch("/auth/verify-2fa", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ code })
        });

        const data = await response.json();

        if (!response.ok) {
            twoFactorMessage.innerHTML = `
                <div class="alert alert-danger">
                    ${data.error}
                </div>
            `;
            return;
        }

        currentUser = data.user;
        authCard.classList.add("dashboard-active");
        showDashboard();

    } catch (error) {
        twoFactorMessage.innerHTML = `
            <div class="alert alert-danger">
                Não foi possível conectar ao servidor.
            </div>
        `;
    }
});

// DASHBOARD E 2FA

function showDashboard() {
    loginSection.classList.add("d-none");
    twoFactorSection.classList.add("d-none");
    registerSection.classList.add("d-none");
    dashboardSection.classList.remove("d-none");
    document.getElementById("dashboardUserName").textContent = currentUser.full_name;
    showDashboardScreen("overviewScreen");

    // Exibir informações do usuário
    const userInfo = document.getElementById("userInfo");
    userInfo.innerHTML = `
        <strong>Nome completo:</strong> ${currentUser.full_name}<br>
        <strong>Usuário:</strong> ${currentUser.username}<br>
        <strong>E-mail:</strong> ${currentUser.email}
    `;

    // Carregar status de 2FA
    loadTwoFactorStatus();
    loadTutoringOffers();
}

async function loadTwoFactorStatus() {
    try {
        const response = await fetch(`/auth/2fa/status?user_id=${currentUser.id}`);
        const data = await response.json();

        const statusDiv = document.getElementById("twoFactorStatus");
        const setup2faSection = document.getElementById("setup2faSection");
        const disable2faSection = document.getElementById("disable2faSection");

        if (data.two_factor_enabled) {
            statusDiv.innerHTML = `
                <div class="alert alert-success">
                    ✓ 2FA está <strong>ativado</strong>
                </div>
            `;
            setup2faSection.classList.add("d-none");
            disable2faSection.classList.remove("d-none");
        } else {
            statusDiv.innerHTML = `
                <div class="alert alert-warning">
                    2FA não está ativado
                </div>
            `;
            setup2faSection.classList.remove("d-none");
            disable2faSection.classList.add("d-none");

            // Se a seção de setup está visível, gerar novo QR code
            const setupForm = setup2faSection.querySelector("form");
            if (!setupForm.dataset.qrGenerated) {
                generateTwoFactorQR();
                setupForm.dataset.qrGenerated = "true";
            }
        }
    } catch (error) {
        console.error("Erro ao carregar status 2FA:", error);
    }
}

async function generateTwoFactorQR() {
    try {
        const response = await fetch("/auth/2fa/setup", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ user_id: currentUser.id })
        });

        const data = await response.json();

        if (!response.ok) {
            setupTwoFactorMessage.innerHTML = `
                <div class="alert alert-danger">
                    Erro ao gerar QR code: ${data.error}
                </div>
            `;
            return;
        }

        // Armazenar o segredo temporário
        pendingTwoFactorSecret = data.secret;

        // Exibir QR code
        const qrContainer = document.getElementById("qrCodeContainer");
        qrContainer.innerHTML = `<img src="${data.qr_code}" alt="QR Code" style="max-width: 200px;">`;

        // Exibir chave manual
        const keyContainer = document.getElementById("manualKeyContainer");
        keyContainer.textContent = data.manual_entry_key;

    } catch (error) {
        setupTwoFactorMessage.innerHTML = `
            <div class="alert alert-danger">
                Não foi possível conectar ao servidor.
            </div>
        `;
    }
}

confirmTwoFactorForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    setupTwoFactorMessage.innerHTML = "";

    const code = document.getElementById("setupTwoFactorCode").value;

    if (!pendingTwoFactorSecret) {
        setupTwoFactorMessage.innerHTML = `
            <div class="alert alert-danger">
                Segredo não foi gerado. Tente novamente.
            </div>
        `;
        return;
    }

    try {
        const response = await fetch("/auth/2fa/confirm", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                user_id: currentUser.id,
                secret: pendingTwoFactorSecret,
                code
            })
        });

        const data = await response.json();

        if (!response.ok) {
            setupTwoFactorMessage.innerHTML = `
                <div class="alert alert-danger">
                    ${data.error}
                </div>
            `;
            return;
        }

        setupTwoFactorMessage.innerHTML = `
            <div class="alert alert-success">
                ${data.message}
            </div>
        `;

        confirmTwoFactorForm.reset();
        document.getElementById("setupTwoFactorCode").value = "";

        // Recarregar status após 2 segundos
        setTimeout(loadTwoFactorStatus, 2000);

    } catch (error) {
        setupTwoFactorMessage.innerHTML = `
            <div class="alert alert-danger">
                Não foi possível conectar ao servidor.
            </div>
        `;
    }
});

disableTwoFactorForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    disableTwoFactorMessage.innerHTML = "";

    const password = document.getElementById("disableTwoFactorPassword").value;

    try {
        const response = await fetch("/auth/2fa/disable", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                user_id: currentUser.id,
                password
            })
        });

        const data = await response.json();

        if (!response.ok) {
            disableTwoFactorMessage.innerHTML = `
                <div class="alert alert-danger">
                    ${data.error}
                </div>
            `;
            return;
        }

        disableTwoFactorMessage.innerHTML = `
            <div class="alert alert-success">
                ${data.message}
            </div>
        `;

        disableTwoFactorForm.reset();
        document.getElementById("disableTwoFactorPassword").value = "";

        // Recarregar status após 2 segundos
        setTimeout(loadTwoFactorStatus, 2000);

    } catch (error) {
        disableTwoFactorMessage.innerHTML = `
            <div class="alert alert-danger">
                Não foi possível conectar ao servidor.
            </div>
        `;
    }
});

window.addEventListener("DOMContentLoaded", async () => {
    // Verifica se a página foi aberta através de um link de recuperação.
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get("token");

    if (token) {
        // Se existe token, mostra diretamente a tela de redefinição.
        loginSection.classList.add("d-none");
        registerSection.classList.add("d-none");
        forgotPasswordSection.classList.add("d-none");
        twoFactorSection.classList.add("d-none");
        dashboardSection.classList.add("d-none");
        resetPasswordSection.classList.remove("d-none");

        return;
    }

    // Caso contrário, verifica se já existe um cookie de sessão válido.
    try {
        const response = await fetch("/auth/me");

        if (response.ok) {
            const data = await response.json();
            currentUser = data.user;
            authCard.classList.add("dashboard-active");
            showDashboard();
        }
    } catch (error) {
        console.error("Erro ao verificar sessão ativa:", error);
    }
});