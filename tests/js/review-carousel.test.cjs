const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const sourcePath = path.resolve(__dirname, "../../static/js/global/site.js");
const source = fs.readFileSync(sourcePath, "utf8");

class FakeElement {
    constructor(className = "") {
        this.className = className;
        this.dataset = {};
        this.style = {};
        this.attributes = {};
        this.children = [];
        this.listeners = {};
        this.disabled = false;
        this.hidden = false;
        this.clientWidth = 320;
        this.offsetHeight = 180;
        this.classList = {
            values: new Set(className.split(/\s+/).filter(Boolean)),
            toggle: (name, force) => {
                if (force) {
                    this.classList.values.add(name);
                } else {
                    this.classList.values.delete(name);
                }
            },
            contains: (name) => this.classList.values.has(name),
        };
    }

    addEventListener(type, listener) {
        this.listeners[type] = [...(this.listeners[type] || []), listener];
    }

    dispatch(type, event = {}) {
        (this.listeners[type] || []).forEach((listener) => listener({
            preventDefault() {},
            ...event,
        }));
    }

    appendChild(child) {
        child.parentElement = this;
        this.children.push(child);
    }

    setAttribute(name, value) {
        this.attributes[name] = value;
    }

    removeAttribute(name) {
        delete this.attributes[name];
    }

    contains(target) {
        return this === target || this.children.includes(target);
    }

    querySelector(selector) {
        return this.elements?.[selector] || null;
    }

    querySelectorAll(selector) {
        if (selector === ".home-review-slide") {
            return this.slides || [];
        }
        return [];
    }
}

function createHarness(slideCount, reducedMotion = false) {
    const slides = Array.from({ length: slideCount }, (_, index) => {
        const slide = new FakeElement("home-review-slide");
        slide.offsetHeight = 180 + index * 20;
        return slide;
    });
    const viewport = new FakeElement("home-reviews-viewport");
    const track = new FakeElement("home-reviews-track");
    track.slides = slides;
    const prevButton = new FakeElement("review-prev");
    const nextButton = new FakeElement("review-next");
    const dotsContainer = new FakeElement("review-carousel-dots");
    const parent = new FakeElement();
    parent.elements = { ".review-carousel-dots": dotsContainer };
    const carousel = new FakeElement("reviews-carousel-wrapper");
    carousel.parentElement = parent;
    carousel.elements = {
        ".home-reviews-viewport": viewport,
        ".home-reviews-track": track,
        ".review-prev": prevButton,
        ".review-next": nextButton,
    };
    carousel.contains = (target) => [
        carousel, prevButton, nextButton, viewport, dotsContainer,
    ].includes(target);

    const documentListeners = {};
    const document = {
        visibilityState: "visible",
        addEventListener(type, listener) {
            documentListeners[type] = [
                ...(documentListeners[type] || []),
                listener,
            ];
        },
        createElement() {
            return new FakeElement();
        },
    };
    const mediaQuery = {
        matches: reducedMotion,
        addEventListener(type, listener) {
            this.listener = listener;
        },
    };
    const timers = new Map();
    let nextTimerId = 1;
    const window = {
        matchMedia: () => mediaQuery,
        addEventListener() {},
        setTimeout(callback, delay) {
            const id = nextTimerId++;
            timers.set(id, { callback, delay });
            return id;
        },
        clearTimeout(id) {
            timers.delete(id);
        },
    };

    const context = vm.createContext({ document, window });
    vm.runInContext(source, context);
    context.initReviewCarousel(carousel);

    return {
        carousel,
        context,
        document,
        documentListeners,
        dotsContainer,
        mediaQuery,
        nextButton,
        prevButton,
        slides,
        timers,
        track,
        viewport,
        window,
        advanceTimer() {
            assert.equal(timers.size, 1, "exactly one autoplay timer is active");
            const [[id, timer]] = timers;
            timers.delete(id);
            assert.equal(timer.delay, 5000);
            timer.callback();
        },
    };
}

test("previous and next buttons wrap and indicators follow the active review", () => {
    const harness = createHarness(3);

    harness.context.initReviewCarousel(harness.carousel);
    assert.equal(harness.nextButton.listeners.click.length, 1);
    assert.equal(harness.timers.size, 1);
    harness.nextButton.dispatch("click");
    assert.equal(harness.track.style.transform, "translate3d(-320px, 0, 0)");
    assert.equal(harness.dotsContainer.children[1].attributes["aria-current"], "true");

    harness.nextButton.dispatch("click");
    harness.nextButton.dispatch("click");
    assert.equal(harness.track.style.transform, "translate3d(0px, 0, 0)");

    harness.prevButton.dispatch("click");
    assert.equal(harness.track.style.transform, "translate3d(-640px, 0, 0)");
});

test("autoplay advances every five seconds and manual navigation keeps one timer", () => {
    const harness = createHarness(3);
    assert.equal(harness.timers.size, 1);
    harness.advanceTimer();
    assert.equal(harness.track.style.transform, "translate3d(-320px, 0, 0)");
    assert.equal(harness.timers.size, 1);

    harness.nextButton.dispatch("click");
    assert.equal(harness.timers.size, 1);
});

test("autoplay pauses and resumes for hover, focus, hidden tabs, and reduced motion", () => {
    const harness = createHarness(2);

    harness.viewport.dispatch("mouseenter");
    assert.equal(harness.timers.size, 0);
    harness.viewport.dispatch("mouseleave");
    assert.equal(harness.timers.size, 1);

    harness.carousel.dispatch("focusin");
    assert.equal(harness.timers.size, 0);
    harness.carousel.dispatch("focusout", { relatedTarget: null });
    assert.equal(harness.timers.size, 1);

    harness.document.visibilityState = "hidden";
    harness.documentListeners.visibilitychange[0]();
    assert.equal(harness.timers.size, 0);
    harness.document.visibilityState = "visible";
    harness.documentListeners.visibilitychange[0]();
    assert.equal(harness.timers.size, 1);

    harness.mediaQuery.matches = true;
    harness.mediaQuery.listener();
    assert.equal(harness.timers.size, 0);
    harness.mediaQuery.matches = false;
    harness.mediaQuery.listener();
    assert.equal(harness.timers.size, 1);

    const reducedMotionHarness = createHarness(2, true);
    assert.equal(reducedMotionHarness.timers.size, 0);
});

test("keyboard and touch navigation work, including reverse wrapping", () => {
    const harness = createHarness(2);
    let prevented = false;
    harness.carousel.dispatch("keydown", {
        key: "ArrowLeft",
        preventDefault() {
            prevented = true;
        },
    });
    assert.equal(prevented, true);
    assert.equal(harness.track.style.transform, "translate3d(-320px, 0, 0)");

    harness.viewport.dispatch("touchstart", {
        changedTouches: [{ clientX: 200 }],
    });
    harness.viewport.dispatch("touchend", {
        changedTouches: [{ clientX: 100 }],
    });
    assert.equal(harness.track.style.transform, "translate3d(0px, 0, 0)");
});

test("empty and single-review carousels do not start autoplay", () => {
    const empty = createHarness(0);
    assert.equal(empty.prevButton.hidden, true);
    assert.equal(empty.nextButton.hidden, true);
    assert.equal(empty.dotsContainer.hidden, true);
    assert.equal(empty.timers.size, 0);

    const single = createHarness(1);
    assert.equal(single.prevButton.disabled, true);
    assert.equal(single.nextButton.disabled, true);
    assert.equal(single.timers.size, 0);
});
