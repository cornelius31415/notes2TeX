const fileInput = document.getElementById("file");
const preview = document.getElementById("preview");
const btn = document.getElementById("btn");

// 🧠 speichert ggf. konvertierte Datei
let selectedFile = null;

fileInput.addEventListener("change", async () => {
    let file = fileInput.files[0];
    if (!file) return;

    // 🟡 HEIC DETECTION
    const isHeic =
        file.type === "image/heic" ||
        file.name.toLowerCase().endsWith(".heic");

    // 🔥 CONVERT HEIC → JPG
    if (isHeic && typeof heic2any !== "undefined") {
        try {
            const blob = await heic2any({
                blob: file,
                toType: "image/jpeg",
                quality: 0.9
            });

            file = new File(
                [blob],
                file.name.replace(".heic", ".jpg"),
                { type: "image/jpeg" }
            );

            console.log("HEIC → JPG konvertiert");
        } catch (err) {
            console.error("HEIC conversion failed:", err);
            alert("HEIC konnte nicht konvertiert werden.");
            return;
        }
    }

    // 💾 speichere Datei für Upload
    selectedFile = file;

    // 🖼️ Preview
    const reader = new FileReader();
    reader.onload = (e) => {
        preview.src = e.target.result;
        preview.hidden = false;

        btn.hidden = false;
    };

    reader.readAsDataURL(file);
});




async function send() {

    const file = fileInput.files[0];

    if (!file) return;

    // Loading anzeigen
    document.getElementById("loading").style.display = "block";

    // Button deaktivieren
    btn.disabled = true;

    const formData = new FormData();
    formData.append("file", file);

    try {

        const res = await fetch("/api/bild-zu-text", {
            method: "POST",
            body: formData
        });

        const data = await res.json();

        const latex = data.latex;

        // Code anzeigen
        document.getElementById("code").innerText = latex;

        // Preview rendern
        katex.render(latex, document.getElementById("render"), {
            throwOnError: false,
            displayMode: true
        });

    } catch (err) {

        document.getElementById("code").innerText =
            "Fehler: " + err.message;
    }

    finally {

        // ✅ Loading wieder verstecken
        document.getElementById("loading").style.display = "none";

        // ✅ Button wieder aktivieren
        btn.disabled = false;
    }
}






function copyLatex() {
    const text = document.getElementById("code").innerText;

    navigator.clipboard.writeText(text)
        .then(() => {
            const btn = document.querySelector(".copy-btn");
            btn.innerText = "✔ Copied";

            setTimeout(() => {
                btn.innerText = "📋 Copy";
            }, 1500);
        })
        .catch(err => {
            console.error("Copy failed:", err);
        });
}






function exportPDF() {
    const printContent = document.getElementById("render").innerHTML;

    const win = window.open("", "", "width=800,height=600");

    win.document.write(`
        <html>
        <head>
            <title>LaTeX Export</title>

            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">

            <style>
                body {
                    font-family: Arial;
                    padding: 40px;
                }
            </style>
        </head>
        <body>
            ${printContent}
            <script>
                window.onload = () => window.print();
            <\/script>
        </body>
        </html>
    `);

    win.document.close();
}