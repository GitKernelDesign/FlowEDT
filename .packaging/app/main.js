"use strict";

// Enveloppe de bureau de Flow-EDT : une seule fenêtre, aucun accès réseau,
// les données restent dans le navigateur embarqué (localStorage).

const { app, BrowserWindow, Menu, dialog, shell, session } = require("electron");
const path = require("node:path");
const fs = require("node:fs");

const APP_ID = "fr.flowedt.FlowEDT";
const PRODUCT = "Flow-EDT";

// Vérification d'intégration : FLOWEDT_SMOKE=<dossier> charge la fenêtre,
// contrôle que l'application démarre, écrit une capture puis quitte.
const SMOKE_DIR = process.env.FLOWEDT_SMOKE || "";

// Version portable : un fichier portable.txt à côté de l'exécutable place les
// données dans le dossier de l'application au lieu du profil utilisateur.
function portableRoot() {
    if (!app.isPackaged && process.env.FLOWEDT_PORTABLE !== "1") return null;
    if (process.env.FLOWEDT_PORTABLE === "1") return path.dirname(app.getPath("exe"));
    const marker = path.join(path.dirname(app.getPath("exe")), "portable.txt");
    return fs.existsSync(marker) ? path.dirname(app.getPath("exe")) : null;
}

const portable = portableRoot();
if (portable) {
    app.setPath("userData", path.join(portable, "FlowEDT-data"));
    app.setPath("sessionData", path.join(portable, "FlowEDT-data"));
}

app.setName(PRODUCT);
app.setAppUserModelId(APP_ID);
// La classe X11 des fenêtres découle du nom de l'application : « flow-edt ».
// Le fichier .desktop la reprend dans StartupWMClass pour associer l'icône.

let mainWindow = null;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1280,
        height: 900,
        minWidth: 360,
        minHeight: 520,
        backgroundColor: "#f6fbfa",
        icon: path.join(__dirname, "icon.png"),
        show: false,
        autoHideMenuBar: process.platform !== "darwin",
        webPreferences: {
            contextIsolation: true,
            nodeIntegration: false,
            sandbox: true,
            spellcheck: false,
        },
    });

    mainWindow.once("ready-to-show", () => {
        mainWindow.show();
    });

    mainWindow.loadFile(path.join(__dirname, "index.html"));

    if (SMOKE_DIR) runSmokeTest(mainWindow);

    // Le bouton « Exporter en PDF » ouvre une fenêtre vide puis y écrit le
    // document à imprimer : on autorise ces fenêtres, jamais un site distant.
    mainWindow.webContents.setWindowOpenHandler(({ url }) => {
        if (url === "about:blank" || url.startsWith("file:")) {
            return {
                action: "allow",
                overrideBrowserWindowOptions: {
                    width: 1024,
                    height: 780,
                    autoHideMenuBar: true,
                    icon: path.join(__dirname, "icon.png"),
                    webPreferences: { contextIsolation: true, sandbox: true },
                },
            };
        }
        if (/^https?:/i.test(url)) shell.openExternal(url);
        return { action: "deny" };
    });

    // Aucune navigation hors du fichier livré.
    mainWindow.webContents.on("will-navigate", (event, url) => {
        if (!url.startsWith("file:")) {
            event.preventDefault();
            if (/^https?:/i.test(url)) shell.openExternal(url);
        }
    });

    mainWindow.on("closed", () => {
        mainWindow = null;
    });
}

// Contrôle de démarrage utilisé par .packaging/build.py --smoke.
function runSmokeTest(win) {
    const messages = [];
    win.webContents.on("console-message", (event) => {
        const levelNames = ["debug", "info", "warning", "error"];
        const level =
            typeof event.level === "number" ? levelNames[event.level] || "info" : event.level;
        if (level === "error" || level === "warning") {
            messages.push(`${level}: ${event.message}`);
        }
    });
    win.webContents.on("render-process-gone", (_event, details) => {
        messages.push(`renderer: ${details.reason}`);
    });

    win.webContents.once("did-finish-load", async () => {
        const report = { ok: false, messages };
        try {
            const probe = await win.webContents.executeJavaScript(
                `(() => {
                    const tabs = [...document.querySelectorAll("[data-tab]")]
                        .map((node) => node.dataset.tab);
                    const active = document.documentElement.dataset.tab || "";
                    return {
                        title: document.title,
                        version: document.body.dataset.version || "",
                        lang: document.documentElement.lang,
                        tabs: [...new Set(tabs)].filter(Boolean),
                        tab: active,
                        heading: (document.querySelector("h1") || {}).textContent || "",
                        courses: document.querySelectorAll(".slot-course").length,
                        rows: document.querySelectorAll("table tbody tr").length,
                        width: window.innerWidth,
                        height: window.innerHeight,
                    };
                })()`,
                true
            );
            Object.assign(report, probe);
            report.ok = Boolean(probe.title && probe.tabs.length >= 4 && probe.rows > 0);
        } catch (error) {
            messages.push(`probe: ${error.message}`);
        }

        await new Promise((resolve) => setTimeout(resolve, 800));
        try {
            const image = await win.webContents.capturePage();
            fs.writeFileSync(path.join(SMOKE_DIR, "window.png"), image.toPNG());
            report.capture = image.getSize();
        } catch (error) {
            messages.push(`capture: ${error.message}`);
        }

        console.log(`SMOKE ${JSON.stringify(report)}`);
        app.exit(report.ok ? 0 : 1);
    });
}

function buildMenu() {

    const isMac = process.platform === "darwin";
    const template = [
        ...(isMac
            ? [
                  {
                      label: PRODUCT,
                      submenu: [
                          { role: "about", label: `À propos de ${PRODUCT}` },
                          { type: "separator" },
                          { role: "hide", label: "Masquer" },
                          { role: "hideOthers", label: "Masquer les autres" },
                          { type: "separator" },
                          { role: "quit", label: "Quitter" },
                      ],
                  },
              ]
            : []),
        {
            label: "Fichier",
            submenu: [
                {
                    label: "Imprimer…",
                    accelerator: "CmdOrCtrl+P",
                    click: () => mainWindow && mainWindow.webContents.print({}),
                },
                { type: "separator" },
                isMac ? { role: "close", label: "Fermer" } : { role: "quit", label: "Quitter" },
            ],
        },
        {
            label: "Édition",
            submenu: [
                { role: "undo", label: "Annuler" },
                { role: "redo", label: "Rétablir" },
                { type: "separator" },
                { role: "cut", label: "Couper" },
                { role: "copy", label: "Copier" },
                { role: "paste", label: "Coller" },
                { role: "selectAll", label: "Tout sélectionner" },
            ],
        },
        {
            label: "Affichage",
            submenu: [
                { role: "reload", label: "Recharger" },
                { role: "resetZoom", label: "Zoom normal" },
                { role: "zoomIn", label: "Agrandir" },
                { role: "zoomOut", label: "Réduire" },
                { type: "separator" },
                { role: "togglefullscreen", label: "Plein écran" },
            ],
        },
        {
            label: "Aide",
            submenu: [
                {
                    label: `À propos de ${PRODUCT}`,
                    click: () => {
                        dialog.showMessageBox({
                            type: "info",
                            title: `À propos de ${PRODUCT}`,
                            message: `${PRODUCT} ${app.getVersion()}`,
                            detail:
                                "Générateur d'emplois du temps pour établissement scolaire.\n" +
                                "Licence GPL-3.0 — aucune donnée ne quitte ce poste.\n" +
                                "https://github.com/GitKernelDesign/FlowEDT",
                            buttons: ["Fermer"],
                        });
                    },
                },
                {
                    label: "Licence GPL-3.0",
                    click: () => shell.openPath(path.join(__dirname, "LICENSE")),
                },
            ],
        },
    ];
    Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

const singleInstance = app.requestSingleInstanceLock();
if (!singleInstance) {
    app.quit();
} else {
    app.on("second-instance", () => {
        if (!mainWindow) return;
        if (mainWindow.isMinimized()) mainWindow.restore();
        mainWindow.focus();
    });

    app.whenReady().then(() => {
        // Les exports CSV sont enregistrés par défaut dans Téléchargements.
        session.defaultSession.on("will-download", () => {});
        buildMenu();
        createWindow();

        app.on("activate", () => {
            if (BrowserWindow.getAllWindows().length === 0) createWindow();
        });
    });

    app.on("window-all-closed", () => {
        if (process.platform !== "darwin") app.quit();
    });
}
