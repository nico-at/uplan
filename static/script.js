const translations = {
    de: {
        title: "u:plan",
        description: "Erstelle ICS-Feeds für Deine Lehrveranstaltungen ohne Verletzung der <a href='https://ufind.univie.ac.at/de/help.html#disclaimer' target='_blank'>u:find Nutzungsbedingungen</a>. Diese Feeds können zu den meisten Kalendern wie iOS Kalender oder Google Kalender hinzugefügt werden und halten Deinen Zeitplan immer aktuell.",
        coursesLabel: "Lehrveranstaltungen",
        coursesPlaceholder: "IDs durch Beistrich getrennt, z.B. 051011,051012-3,051131-5",
        semesterLabel: "Semester",
        submitButton: "ICS-Feed erstellen",
        disclaimer: "<strong>Haftungsausschluss:</strong> Diese Anwendung wird nicht von der Universität Wien bereitgestellt. Die Universität Wien übernimmt keine Verantwortung für die Datengenauigkeit und haftet nicht für etwaige Schäden, die Nutzern oder Dritten im Zusammenhang mit der Nutzung dieser Daten entstehen.",
        imprintLink: "Impressum",
        privacyLink: "Datenschutz",
        loadingMessage: "Dein ICS-Feed wird generiert, das kann einige Sekunden dauern...",
        rateLimitMessage: "Zu viele Anfragen. Bitte versuche es später erneut."
    },
    en: {
        title: "u:plan",
        description: "Create automatically updating ICS feeds for your courses without violating the <a href='https://ufind.univie.ac.at/en/help.html#disclaimer' target='_blank'>u:find terms</a>. These feeds can be easily added to any calendar app like iOS Calendar or Google Calendar, keeping your schedule always up to date.",
        coursesLabel: "Course IDs",
        coursesPlaceholder: "Comma-separated e.g.,  051011,051012-3,051131-5",
        semesterLabel: "Semester",
        submitButton: "Create ICS Feed",
        disclaimer: "<strong>Disclaimer:</strong> This application is not provided by the University of Vienna. The University of Vienna assumes no responsibility for data accuracy and is not liable for any damages incurred by users or third parties in connection with the use of this data.",
        imprintLink: "Imprint",
        privacyLink: "Data Privacy",
        loadingMessage: "Generating your ICS feed, this might take a few seconds...",
        rateLimitMessage: "Too many requests. Please try again later."
    }
};

let currentLanguage = 'de';

function setLanguage(lang) {
    currentLanguage = lang;
    document.documentElement.lang = lang;
    document.getElementById('title').textContent = translations[lang].title;
    document.getElementById('description').innerHTML = translations[lang].description;
    document.getElementById('coursesLabel').textContent = translations[lang].coursesLabel;
    document.getElementById('courses').placeholder = translations[lang].coursesPlaceholder
    document.getElementById('semesterLabel').textContent = translations[lang].semesterLabel;
    document.getElementById('submitButton').textContent = translations[lang].submitButton;
    document.getElementById('disclaimer').innerHTML = translations[lang].disclaimer;
    //document.getElementById('imprintLink').textContent = translations[lang].imprintLink;
    //document.getElementById('privacyLink').textContent = translations[lang].privacyLink;
    document.getElementById('languageToggle').textContent = lang === 'de' ? 'en' : 'de';
}

document.getElementById('languageToggle').addEventListener('click', function () {
    setLanguage(currentLanguage === 'de' ? 'en' : 'de');
});

setLanguage('de');

document.getElementById('planForm').addEventListener('submit', function (e) {
    e.preventDefault();

    const courses = document.getElementById('courses').value.replace(/\s+/g, '');
    const semester = document.getElementById('semester').value.replace(/\s+/g, '');
    const resultDiv = document.getElementById('result');
    const submitButton = document.querySelector('button[type="submit"]');

    resultDiv.innerHTML = translations[currentLanguage].loadingMessage;
    resultDiv.className = 'success';
    submitButton.disabled = true;

    fetch(`/create?courses=${courses}&semester=${semester}`)
        .then(async response => {
            if (response.ok) {
                return response.json();
            } else if (response.status === 429) {
                throw new Error(translations[lang].rateLimitMessage);
            }
            else {
                const err = await response.json();
                throw new Error(err.detail || `HTTP ${response.status}`);
            }
        })
        .then(data => {
            resultDiv.innerHTML = `ICS-Feed URL: <strong>${data.url}</strong></br></br>${data.courses.join('\n')}`;
            resultDiv.className = 'success';
        })
        .catch(error => {
            resultDiv.textContent = `${error.message}`;
            resultDiv.className = 'error';
        }).finally(() => {
            submitButton.disabled = false;
        });
});