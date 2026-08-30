const loginSection = document.getElementById("loginSection");
const registerSection = document.getElementById("registerSection");

const loginForm = document.getElementById("loginForm");
const registerForm = document.getElementById("registerForm");

const loginMessage = document.getElementById("loginMessage");
const registerMessage = document.getElementById("registerMessage");

const showRegister = document.getElementById("showRegister");
const showLogin = document.getElementById("showLogin");


// Alterna da tela de login para cadastro.
showRegister.addEventListener("click", () => {
    loginSection.classList.add("d-none");
    registerSection.classList.remove("d-none");

    loginMessage.innerHTML = "";
});


// Alterna da tela de cadastro para login.
showLogin.addEventListener("click", () => {
    registerSection.classList.add("d-none");
    loginSection.classList.remove("d-none");

    registerMessage.innerHTML = "";
});


// Cadastro de usuário.
registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    registerMessage.innerHTML = "";

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


// Login do usuário.
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

        loginMessage.innerHTML = `
            <div class="alert alert-success">
                ${data.message}
            </div>
        `;

        loginForm.reset();

    } catch (error) {
        loginMessage.innerHTML = `
            <div class="alert alert-danger">
                Não foi possível conectar ao servidor.
            </div>
        `;
    }
});