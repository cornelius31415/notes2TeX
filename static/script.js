const fileInput = document.getElementById("file");
const preview = document.getElementById("preview");
const btn = document.getElementById("btn");
const loading = document.getElementById("loading");

function setLoading(state) {
    const el = document.getElementById("loading");
    if (!el) return;
    el.style.display = state ? "block" : "none";
}

let selectedFile = null;

/* =========================
   FILE UPLOAD + PREVIEW
========================= */

fileInput.addEventListener("change", async () => {

    let file = fileInput.files[0];
    if (!file) return;

    // HEIC detection
    const isHeic =
        file.type === "image/heic" ||
        file.name.toLowerCase().endsWith(".heic");

    // HEIC → JPG
    if (isHeic && typeof heic2any !== "undefined") {

        try {

            const blob = await heic2any({
                blob: file,
                toType: "image/jpeg",
                quality: 0.9
            });

            file = new File(
                [blob],
                file.name.replace(/\.heic$/i, ".jpg"),
                { type: "image/jpeg" }
            );

        } catch (err) {
            console.error("HEIC conversion failed:", err);
            alert("HEIC konnte nicht konvertiert werden.");
            return;
        }
    }

    // save file
    selectedFile = file;

    // preview image
    const reader = new FileReader();

    reader.onload = (e) => {
        preview.src = e.target.result;
        preview.hidden = false;
        btn.hidden = false;
    };

    reader.readAsDataURL(file);
});


/* =========================
   SEND IMAGE TO BACKEND
========================= */

async function send() {

    const file = selectedFile;

    if (!file) return;

    btn.disabled = true;

    setLoading(true);


    // 👉 WICHTIG: NICHT hidden verwenden
    loading.style.display = "block";

    const formData = new FormData();
    formData.append("file", file);

    try {

        const res = await fetch("/api/bild-zu-text", {
            method: "POST",
            body: formData
        });

        if (!res.ok) {
            throw new Error("Server Error");
        }

        const data = await res.json();

        const latex = data.latex || "";

        document.getElementById("code").innerText = latex;

        katex.render(
            `\\\\begin{aligned}
            ${latex}
        \\\\end{aligned}`,
            document.getElementById("render"),
            {
                throwOnError: false,
                displayMode: true
            }
        );

    } catch (err) {

        document.getElementById("code").innerText =
            "Fehler: " + err.message;

    } finally {

        // 🔥 FORCE UI UPDATE (wichtig für online!)
        setTimeout(() => {
            setLoading(false);
            btn.disabled = false;
        }, 50);
    }
}




/* =========================
   COPY LATEX
========================= */

function copyLatex() {

    const text = document.getElementById("code").innerText;

    navigator.clipboard.writeText(text)

        .then(() => {

            const btn = document.querySelector(".copy-btn");

            btn.innerHTML = "✔";

            setTimeout(() => {

                btn.innerHTML = `
                    <svg class="copy-icon" viewBox="0 0 24 24">
                        <path fill="currentColor"
                        d="M16 1H4c-1.1 0-2 .9-2 2v12h2V3h12V1zm3
                        4H8c-1.1 0-2 .9-2 2v14c0 1.1.9
                        2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0
                        16H8V7h11v14z"/>
                    </svg>
                `;

            }, 1200);
        })

        .catch(err => {
            console.error("Copy failed:", err);
        });
}


/* =========================
   EXPORT PDF
========================= */

function exportPDF() {

    const content =
        document.getElementById("render").innerHTML;

    const win =
        window.open("", "", "width=900,height=700");

    win.document.write(`
        <html>
        <head>
            <title>Export</title>
            <link rel="stylesheet"
                href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
            <style>
                body {
                    font-family: Arial;
                    padding: 40px;
                }
            </style>
        </head>
        <body>
            ${content}
            <script>
                window.onload = () => window.print();
            <\/script>
        </body>
        </html>
    `);

    win.document.close();
}