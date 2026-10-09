/*
=========================================================
YD COMMERCIAL CLEANING
CLEANING CHALLENGE — PHASE 2
=========================================================
*/


(function () {
    "use strict";


    /*
    =====================================================
    DATA
    =====================================================
    */

    const questions =
        Array.isArray(
            window.CLEANING_GAME_QUESTIONS
        )
            ? window.CLEANING_GAME_QUESTIONS
            : [];


    const game =
        document.getElementById(
            "cleaningGame"
        );


    if (
        !game ||
        !questions.length
    ) {
        return;
    }


    /*
    =====================================================
    ELEMENTS
    =====================================================
    */

    const introScreen =
        document.getElementById(
            "introScreen"
        );

    const gameScreen =
        document.getElementById(
            "gameScreen"
        );

    const resultScreen =
        document.getElementById(
            "resultScreen"
        );

    const startGameButton =
        document.getElementById(
            "startGameButton"
        );

    const nextQuestionButton =
        document.getElementById(
            "nextQuestionButton"
        );

    const playAgainButton =
        document.getElementById(
            "playAgainButton"
        );

    const questionProgress =
        document.getElementById(
            "questionProgress"
        );

    const questionNumber =
        document.getElementById(
            "questionNumber"
        );

    const questionKicker =
        document.getElementById(
            "questionKicker"
        );

    const scenarioText =
        document.getElementById(
            "scenarioText"
        );

    const questionHeading =
        document.getElementById(
            "questionHeading"
        );

    const answerGrid =
        document.getElementById(
            "answerGrid"
        );

    const answerFeedback =
        document.getElementById(
            "answerFeedback"
        );

    const feedbackIcon =
        document.getElementById(
            "feedbackIcon"
        );

    const feedbackTitle =
        document.getElementById(
            "feedbackTitle"
        );

    const feedbackExplanation =
        document.getElementById(
            "feedbackExplanation"
        );

    const feedbackTip =
        document.getElementById(
            "feedbackTip"
        );

    const questionActions =
        document.getElementById(
            "questionActions"
        );

    const scoreValue =
        document.getElementById(
            "scoreValue"
        );

    const progressFill =
        document.getElementById(
            "progressFill"
        );

    const progressDots =
        document.getElementById(
            "progressDots"
        );

    const finalScore =
        document.getElementById(
            "finalScore"
        );

    const accuracyValue =
        document.getElementById(
            "accuracyValue"
        );

    const correctValue =
        document.getElementById(
            "correctValue"
        );

    const performanceBadge =
        document.getElementById(
            "performanceBadge"
        );

    const bonusStat =
        document.getElementById(
            "bonusStat"
        );

    const resultEyebrow =
        document.getElementById(
            "resultEyebrow"
        );

    const profileHeadline =
        document.getElementById(
            "profileHeadline"
        );

    const resultMessage =
        document.getElementById(
            "resultMessage"
        );

    const resultTip =
        document.getElementById(
            "resultTip"
        );

    const resultCta =
        document.getElementById(
            "resultCta"
        );

    const scoreRing =
        document.getElementById(
            "scoreRing"
        );

    const quoteButton =
        document.getElementById(
            "quoteButton"
        );

    const gameError =
        document.getElementById(
            "gameError"
        );

    const verificationNotice =
        document.getElementById(
            "verificationNotice"
        );


    /*
    =====================================================
    CONSTANTS
    =====================================================
    */

    const MAX_SCORE = 75;

    const POINTS_PER_CORRECT = 10;

    const PERFECT_BONUS = 25;

    const REDUCED_MOTION_QUERY =
        "(prefers-reduced-motion: reduce)";


    /*
    =====================================================
    STATE
    =====================================================
    */

    let currentQuestionIndex = 0;

    let correctAnswers = 0;

    let currentScore = 0;

    let answered = false;

    let resultSubmitted = false;

    let missedCategories = [];

    let selectedAnswers = {};

    let startingGame = false;


    /*
    =====================================================
    ACCESSIBILITY
    =====================================================
    */

    function announce(message) {
        let liveRegion =
            document.getElementById(
                "cleaningGameLiveRegion"
            );

        if (!liveRegion) {
            liveRegion =
                document.createElement(
                    "div"
                );

            liveRegion.id =
                "cleaningGameLiveRegion";

            liveRegion.className =
                "sr-only";

            liveRegion.setAttribute(
                "aria-live",
                "polite"
            );

            liveRegion.setAttribute(
                "aria-atomic",
                "true"
            );

            game.appendChild(
                liveRegion
            );
        }

        liveRegion.textContent = "";

        window.setTimeout(
            function () {
                liveRegion.textContent =
                    message;
            },
            30
        );
    }


    function prefersReducedMotion() {
        return window.matchMedia(
            REDUCED_MOTION_QUERY
        ).matches;
    }


    /*
    =====================================================
    SCREEN MANAGEMENT
    =====================================================
    */

    function showScreen(screen) {
        if (introScreen) {
            introScreen.hidden =
                screen !== introScreen;
        }

        if (gameScreen) {
            gameScreen.hidden =
                screen !== gameScreen;
        }

        if (resultScreen) {
            resultScreen.hidden =
                screen !== resultScreen;
        }
    }


    /*
    =====================================================
    SCORE
    =====================================================
    */

    function updateScore(score) {
        if (!scoreValue) {
            return;
        }

        const safeScore =
            Math.min(
                Math.max(
                    Number(score) || 0,
                    0
                ),
                MAX_SCORE
            );

        scoreValue.textContent =
            String(safeScore);
    }


    /*
    =====================================================
    PROGRESS
    =====================================================
    */

    function buildProgressDots() {
        if (!progressDots) {
            return;
        }

        progressDots.innerHTML = "";

        questions.forEach(
            function () {
                const dot =
                    document.createElement(
                        "span"
                    );

                dot.className =
                    "progress-dot";

                dot.setAttribute(
                    "aria-hidden",
                    "true"
                );

                progressDots.appendChild(
                    dot
                );
            }
        );
    }


    function updateProgress() {
        const total =
            questions.length;

        const current =
            currentQuestionIndex + 1;

        const percentage =
            (current / total) * 100;


        if (questionProgress) {
            questionProgress.textContent =
                `Shift stage ${current} of ${total}`;
        }


        if (questionNumber) {
            questionNumber.textContent =
                String(current).padStart(
                    2,
                    "0"
                );
        }


        if (progressFill) {
            progressFill.style.width =
                `${percentage}%`;
        }


        if (!progressDots) {
            return;
        }


        const dots =
            progressDots.querySelectorAll(
                ".progress-dot"
            );


        dots.forEach(
            function (
                dot,
                index
            ) {
                dot.classList.toggle(
                    "complete",
                    index <
                        currentQuestionIndex
                );

                dot.classList.toggle(
                    "active",
                    index ===
                        currentQuestionIndex
                );
            }
        );
    }


    /*
    =====================================================
    FEEDBACK
    =====================================================
    */

    function clearFeedback() {
        if (answerFeedback) {
            answerFeedback.hidden =
                true;

            answerFeedback.classList.remove(
                "is-incorrect"
            );
        }


        if (questionActions) {
            questionActions.hidden =
                true;
        }


        if (feedbackTip) {
            feedbackTip.hidden =
                true;

            feedbackTip.textContent =
                "";
        }
    }


    /*
    =====================================================
    QUESTION RENDERING
    =====================================================
    */

    function renderQuestion() {
        const question =
            questions[
                currentQuestionIndex
            ];


        if (!question) {
            finishGame();

            return;
        }


        answered = false;

        clearFeedback();

        updateProgress();


        if (questionKicker) {
            questionKicker.textContent =
                question.surface ||
                question.category ||
                "SHIFT DECISION";
        }

        if (scenarioText) {
            scenarioText.textContent =
                question.scenario || "";
        }


        if (questionHeading) {
            questionHeading.textContent =
                question.question || "";

            questionHeading.classList.remove(
                "question-enter"
            );

            void questionHeading.offsetWidth;

            questionHeading.classList.add(
                "question-enter"
            );
        }


        if (!answerGrid) {
            return;
        }


        answerGrid.innerHTML = "";


        const answers =
            Array.isArray(
                question.answers
            )
                ? question.answers
                : [];


        const letters =
            ["A", "B", "C", "D", "E"];


        answers.forEach(
            function (
                answer,
                index
            ) {
                const button =
                    document.createElement(
                        "button"
                    );


                button.type =
                    "button";


                button.className =
                    "answer-button";


                button.dataset.answer =
                    answer;


                button.setAttribute(
                    "aria-label",
                    `Answer ${letters[index]}: ${answer}`
                );


                button.innerHTML = `
                    <span
                        class="answer-letter"
                        aria-hidden="true"
                    >
                        ${letters[index]}
                    </span>

                    <span>
                        ${answer}
                    </span>
                `;


                button.addEventListener(
                    "click",
                    function () {
                        selectAnswer(
                            button,
                            answer,
                            question
                        );
                    }
                );


                answerGrid.appendChild(
                    button
                );
            }
        );


        announce(
            `Question ${
                currentQuestionIndex + 1
            } of ${
                questions.length
            }. ${
                question.question
            }`
        );
    }


    /*
    =====================================================
    ANSWER
    =====================================================
    */

    function selectAnswer(
        selectedButton,
        selectedAnswer,
        question
    ) {
        if (answered) {
            return;
        }


        answered = true;


        const buttons =
            answerGrid.querySelectorAll(
                ".answer-button"
            );


        buttons.forEach(
            function (button) {
                button.disabled =
                    true;

                button.setAttribute(
                    "aria-disabled",
                    "true"
                );
            }
        );


        const isCorrect =
            selectedAnswer ===
            question.correct_answer;

        selectedAnswers[question.id] =
            selectedAnswer;


        if (isCorrect) {

            correctAnswers += 1;

            currentScore +=
                POINTS_PER_CORRECT;


            selectedButton.classList.add(
                "correct"
            );


            if (feedbackTitle) {
                feedbackTitle.textContent =
                    "Correct";
            }


            if (feedbackIcon) {
                feedbackIcon.innerHTML = `
                    <svg
                        class="feedback-icon-svg"
                        viewBox="0 0 24 24"
                        aria-hidden="true"
                    >
                        <path
                            d="m5 12 4 4L19 6"
                        ></path>
                    </svg>
                `;
            }


            announce(
                `Correct answer. You earned ${
                    POINTS_PER_CORRECT
                } points.`
            );

        } else {

            selectedButton.classList.add(
                "incorrect"
            );


            if (
                question.category &&
                !missedCategories.includes(
                    question.category
                )
            ) {
                missedCategories.push(
                    question.category
                );
            }


            buttons.forEach(
                function (button) {

                    if (
                        button.dataset.answer ===
                        question.correct_answer
                    ) {
                        button.classList.add(
                            "correct"
                        );
                    }

                }
            );


            if (feedbackTitle) {
                feedbackTitle.textContent =
                    "Not quite";
            }


            if (answerFeedback) {
                answerFeedback.classList.add(
                    "is-incorrect"
                );
            }


            if (feedbackIcon) {
                feedbackIcon.innerHTML = `
                    <svg
                        class="feedback-icon-svg"
                        viewBox="0 0 24 24"
                        aria-hidden="true"
                    >
                        <path d="M6 6l12 12"></path>
                        <path d="M18 6 6 18"></path>
                    </svg>
                `;
            }


            announce(
                `Incorrect answer. The correct answer is ${
                    question.correct_answer
                }.`
            );
        }


        updateScore(
            currentScore
        );


        if (feedbackExplanation) {
            feedbackExplanation.textContent =
                question.explanation ||
                "";
        }


        if (
            feedbackTip &&
            question.tip
        ) {
            feedbackTip.hidden =
                false;

            feedbackTip.innerHTML = `
                <strong>Quick tip:</strong>
                ${question.tip}
            `;
        }


        if (answerFeedback) {
            answerFeedback.hidden =
                false;
        }


        if (questionActions) {
            questionActions.hidden =
                false;
        }


        if (nextQuestionButton) {
            const label =
                nextQuestionButton.querySelector(
                    "span"
                );

            if (label) {
                label.textContent =
                    currentQuestionIndex ===
                    questions.length - 1
                        ? "Complete Shift"
                        : "Continue Shift";
            }
        }


        if (answerFeedback) {
            answerFeedback.scrollIntoView(
                {
                    behavior:
                        prefersReducedMotion()
                            ? "auto"
                            : "smooth",
                    block: "nearest",
                }
            );
        }
    }


    /*
    =====================================================
    NEXT QUESTION
    =====================================================
    */

    function nextQuestion() {
        if (!answered) {
            return;
        }


        if (
            currentQuestionIndex >=
            questions.length - 1
        ) {
            finishGame();

            return;
        }


        currentQuestionIndex += 1;


        renderQuestion();


        window.setTimeout(
            function () {
                if (questionHeading) {
                    questionHeading.focus(
                        {
                            preventScroll:
                                true,
                        }
                    );
                }
            },
            prefersReducedMotion()
                ? 0
                : 100
        );
    }


    /*
    =====================================================
    PERFORMANCE
    =====================================================
    */

    function getPerformance(score) {
        if (score >= 60) {
            return "Outstanding Shift";
        }

        if (score >= 40) {
            return "Shift Ready";
        }

        if (score >= 20) {
            return "Developing Operative";
        }

        return "Coaching Recommended";
    }


    /*
    =====================================================
    RESULT MESSAGE
    =====================================================
    */

    function getLocalProfile(
        score,
        correct,
        total
    ) {
        const level =
            getPerformance(score);


        const profiles = {
            "Outstanding Shift": {
                eyebrow:
                    "EXCELLENT RESULT",

                headline:
                    "You ran a safe, high-quality shift.",

                message:
                    "Excellent decisions across the site. You followed a safe sequence and protected the quality of the handover.",

                tip:
                    "Keep using the site scope, area-specific equipment and final inspection on every shift.",

                cta:
                    "See how our team maintains that standard.",
            },

            "Shift Ready": {
                eyebrow:
                    "STRONG RESULT",

                headline:
                    "A solid shift with a few things to refine.",

                message:
                    "You made several sound site decisions. A couple of process improvements can help you deliver a more consistent handover.",

                tip:
                    "Keep checking product labels, separating area equipment and working to the site checklist.",

                cta:
                    "Our professional team can take care of the work.",
            },

            "Developing Operative": {
                eyebrow:
                    "GOOD START",

                headline:
                    "Your shift is underway; keep building consistency.",

                message:
                    "Some decisions could affect safety or the finish. Reviewing the site process will help you improve.",

                tip:
                    "Use a written checklist and ask the site contact when the scope or product is unclear.",

                cta:
                    "A trained team can handle the details for you.",
            },

            "Coaching Recommended": {
                eyebrow:
                    "KEEP LEARNING",

                headline:
                    "A safe process comes before a fast clean.",

                message:
                    "This shift exposed some important safety and quality steps. The right site procedure protects both people and surfaces.",

                tip:
                    "Pause when a hazard or unidentified chemical is present, and confirm the safe procedure before continuing.",

                cta:
                    "Prefer to leave the cleaning to a trained team?",
            },
        };


        return (
            profiles[level] ||
            profiles["Coaching Recommended"]
        );
    }


    /*
    =====================================================
    RESULT RING
    =====================================================
    */

    function animateResultRing(score) {
        if (!scoreRing) {
            return;
        }


        const radius = 68;

        const circumference =
            2 *
            Math.PI *
            radius;


        scoreRing.style.strokeDasharray =
            `${circumference}`;


        const percentage =
            Math.min(
                Math.max(
                    score / MAX_SCORE,
                    0
                ),
                1
            );


        const offset =
            circumference *
            (1 - percentage);


        if (
            prefersReducedMotion()
        ) {
            scoreRing.style.strokeDashoffset =
                String(offset);

            return;
        }


        scoreRing.style.strokeDashoffset =
            String(circumference);


        window.requestAnimationFrame(
            function () {
                scoreRing.style.strokeDashoffset =
                    String(offset);
            }
        );
    }


    /*
    =====================================================
    SERVER RESULT
    =====================================================
    */

    async function verifyResult() {
        if (resultSubmitted) {
            return null;
        }


        resultSubmitted = true;


        try {

            const response =
                await fetch(
                    "calculate-result/",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json",

                            "X-CSRFToken":
                                getCsrfToken(),

                            "X-Requested-With":
                                "XMLHttpRequest",
                        },

                        credentials:
                            "same-origin",

                        body: JSON.stringify({
                            answers: selectedAnswers,
                        }),
                    }
                );


            if (!response.ok) {
                throw new Error(
                    "Score verification failed."
                );
            }


            const data =
                await response.json();


            if (
                !data ||
                !data.success ||
                !data.result
            ) {
                throw new Error(
                    "Invalid score response."
                );
            }


            return data.result;

        } catch (error) {

            console.warn(
                "Cleaning Challenge:",
                error
            );

            return null;
        }
    }


    function getCsrfToken() {
        const name =
            "csrftoken=";


        const cookies =
            document.cookie
                .split(";")
                .map(
                    function (
                        cookie
                    ) {
                        return cookie.trim();
                    }
                );


        for (
            const cookie of cookies
        ) {
            if (
                cookie.indexOf(
                    name
                ) === 0
            ) {
                return decodeURIComponent(
                    cookie.substring(
                        name.length
                    )
                );
            }
        }


        return "";
    }


    /*
    =====================================================
    FINISH
    =====================================================
    */

    async function finishGame() {

        const total =
            questions.length;


        const perfectRound =
            correctAnswers ===
            total;


        let finalCalculatedScore =
            currentScore;


        if (perfectRound) {
            finalCalculatedScore +=
                PERFECT_BONUS;
        }


        finalCalculatedScore =
            Math.min(
                Math.max(
                    finalCalculatedScore,
                    0
                ),
                MAX_SCORE
            );


        currentScore =
            finalCalculatedScore;


        const accuracy =
            total
                ? Math.round(
                    (
                        correctAnswers /
                        total
                    ) * 100
                )
                : 0;


        const localProfile =
            getLocalProfile(
                finalCalculatedScore,
                correctAnswers,
                total
            );


        /*
        -------------------------------------------------
        INITIAL RESULT
        -------------------------------------------------
        */

        if (finalScore) {
            finalScore.textContent =
                String(
                    finalCalculatedScore
                );
        }


        if (accuracyValue) {
            accuracyValue.textContent =
                `${accuracy}%`;
        }


        if (correctValue) {
            correctValue.textContent =
                `${correctAnswers} / ${total}`;
        }


        if (performanceBadge) {
            performanceBadge.textContent =
                localProfile
                    ? getPerformance(
                        finalCalculatedScore
                    )
                    : "Coaching Recommended";
        }


        if (resultEyebrow) {
            resultEyebrow.textContent =
                localProfile.eyebrow;
        }


        if (profileHeadline) {
            profileHeadline.textContent =
                localProfile.headline;
        }


        if (resultMessage) {
            resultMessage.textContent =
                localProfile.message;
        }


        if (resultTip) {
            resultTip.textContent =
                localProfile.tip;
        }


        if (resultCta) {
            resultCta.textContent =
                localProfile.cta;
        }


        if (bonusStat) {
            bonusStat.hidden =
                !perfectRound;
        }


        animateResultRing(
            finalCalculatedScore
        );


        showScreen(
            resultScreen
        );


        announce(
            `Challenge complete. You scored ${
                finalCalculatedScore
            } out of ${
                MAX_SCORE
            }. You answered ${
                correctAnswers
            } of ${
                total
            } correctly.`
        );


        /*
        -------------------------------------------------
        SERVER RESULT
        -------------------------------------------------
        */

        const serverResult =
            await verifyResult();


        if (serverResult) {

            const verifiedScore =
                Math.min(
                    Math.max(
                        Number(
                            serverResult.score
                        ) || 0,
                        0
                    ),
                    MAX_SCORE
                );


            currentScore =
                verifiedScore;


            if (finalScore) {
                finalScore.textContent =
                    String(
                        verifiedScore
                    );
            }


            if (
                performanceBadge &&
                serverResult.performance
            ) {
                performanceBadge.textContent =
                    serverResult.performance;
            }


            if (
                serverResult.profile
            ) {

                const profile =
                    serverResult.profile;


                if (
                    resultEyebrow &&
                    profile.eyebrow
                ) {
                    resultEyebrow.textContent =
                        profile.eyebrow;
                }


                if (
                    profileHeadline &&
                    profile.headline
                ) {
                    profileHeadline.textContent =
                        profile.headline;
                }


                if (
                    resultMessage &&
                    profile.message
                ) {
                    resultMessage.textContent =
                        profile.message;
                }


                if (
                    resultTip &&
                    profile.tip
                ) {
                    resultTip.textContent =
                        profile.tip;
                }


                if (
                    resultCta &&
                    profile.cta
                ) {
                    resultCta.textContent =
                        profile.cta;
                }
            }


            animateResultRing(
                verifiedScore
            );
        }


        /*
        -------------------------------------------------
        RESULT FOCUS
        -------------------------------------------------
        */

        const resultTitle =
            document.getElementById(
                "resultTitle"
            );


        if (resultTitle) {

            window.setTimeout(
                function () {
                    resultTitle.focus(
                        {
                            preventScroll:
                                true,
                        }
                    );
                },
                prefersReducedMotion()
                    ? 0
                    : 100
            );
        }
    }

    async function trackEvent(event) {
        const response = await fetch(
            "track-event/",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCsrfToken(),
                    "X-Requested-With": "XMLHttpRequest",
                },
                credentials: "same-origin",
                body: JSON.stringify({ event }),
                keepalive: event === "quote_clicked",
            }
        );

        if (!response.ok) {
            throw new Error("The game event could not be recorded.");
        }

        return response.json();
    }


    /*
    =====================================================
    START
    =====================================================
    */

    function startGame() {
        if (startingGame) {
            return;
        }

        startingGame = true;

        if (startGameButton) {
            startGameButton.disabled = true;
        }

        if (gameError) {
            gameError.hidden = true;
        }

        currentQuestionIndex = 0;

        correctAnswers = 0;

        currentScore = 0;

        answered = false;

        resultSubmitted = false;

        missedCategories = [];

        selectedAnswers = {};

        if (verificationNotice) {
            verificationNotice.hidden = true;
        }


        updateScore(0);

        buildProgressDots();

        showScreen(
            gameScreen
        );

        renderQuestion();


        window.scrollTo({
            top: gameScreen
                ? gameScreen.offsetTop
                : 0,

            behavior:
                prefersReducedMotion()
                    ? "auto"
                    : "smooth",
        });


        window.setTimeout(
            function () {
                if (questionHeading) {
                    questionHeading.focus(
                        {
                            preventScroll:
                                true,
                        }
                    );
                }
            },
            prefersReducedMotion()
                ? 0
                : 100
        );

        startingGame = false;

        if (startGameButton) {
            startGameButton.disabled = false;
        }

        trackEvent("game_started").catch(
            function (error) {
                if (gameError) {
                    gameError.textContent =
                        "Your shift has started, but activity tracking is temporarily unavailable. You can continue playing.";
                    gameError.hidden = false;
                }

                console.warn(
                    "Cleaning Challenge activity tracking failed:",
                    error
                );
            }
        );
    }


    /*
    =====================================================
    EVENTS
    =====================================================
    */

    if (startGameButton) {
        startGameButton.addEventListener(
            "click",
            startGame
        );
    }


    if (nextQuestionButton) {
        nextQuestionButton.addEventListener(
            "click",
            nextQuestion
        );
    }


    if (playAgainButton) {
        playAgainButton.addEventListener(
            "click",
            startGame
        );
    }


    if (quoteButton) {
        quoteButton.addEventListener(
            "click",
            function () {
                trackEvent("quote_clicked").catch(
                    function (error) {
                        console.warn(
                            "Cleaning Challenge:",
                            error
                        );
                    }
                );

                announce(
                    "Opening the cleaning quote page."
                );
            }
        );
    }


    /*
    =====================================================
    INITIALISE
    =====================================================
    */

    buildProgressDots();

    updateProgress();

    updateScore(0);

    showScreen(
        introScreen
    );

})();