/* Nokia 603 store — shared behaviour: bag, drawer, reveal, carousel, colours, compare, buy, checkout */
(() => {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
  const fmt = (n) => new Intl.NumberFormat("ru-RU").format(n) + " ₴";
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------------- catalogue ---------------- */
  const COLORS = {
    black: { name: "Чёрный", panel: "чёрная", hex: "#1c1c1e" },
    white: { name: "Белый", panel: "белая", hex: "#ecebe8" },
    fuchsia: { name: "Фуксия", panel: "фуксия", hex: "#a30d3d" },
    green: { name: "Зелёный", panel: "зелёная", hex: "#3e9a2c" },
    yellow: { name: "Жёлтый", panel: "жёлтая", hex: "#edbe00" },
    blue: { name: "Синий", panel: "синяя", hex: "#1f3fa8" },
  };
  const CONDITIONS = {
    new: { name: "Новый", price: 4499, note: "В заводской упаковке, полная комплектация" },
    refurb: { name: "Восстановленный", price: 2999, note: "Как новый: диагностика, новый аккумулятор" },
  };
  const COVER_PRICE = 349;
  const ADDONS = {
    sd32: { title: "Карта microSD 32 ГБ", price: 299, note: "Класс 10, для музыки и фото" },
    battery: { title: "Аккумулятор Nokia BP‑3L", price: 449, note: "Запасной, 1300 мА·ч" },
    glass: { title: "Защитное стекло 3,5″", price: 199, note: "Закалённое, 0,3 мм" },
    care: { title: "Гарантия+ до 24 месяцев", price: 399, note: "Ещё 12 месяцев сервиса сверх базовой гарантии" },
  };
  const img = (kind, color, size = 800) => `assets/img/${kind}-${color}${size ? "-" + size : ""}.webp`;

  /* ---------------- bag (localStorage) ---------------- */
  const BAG_KEY = "n603-bag-v1";
  const bag = {
    read() {
      try {
        const v = JSON.parse(localStorage.getItem(BAG_KEY) || "[]");
        return Array.isArray(v) ? v : [];
      } catch (e) {
        return [];
      }
    },
    write(items) {
      try {
        localStorage.setItem(BAG_KEY, JSON.stringify(items));
      } catch (e) {
        console.warn("[bag] storage unavailable, keeping in memory", e);
      }
      memory = items;
      renderBag();
    },
    items() {
      const stored = bag.read();
      return stored.length || memory === null ? stored : memory;
    },
    add(line) {
      const items = bag.items();
      const same = items.find((i) => i.sku === line.sku);
      if (same) same.qty += line.qty || 1;
      else items.push({ qty: 1, ...line });
      bag.write(items);
      console.info("[bag] add", line.sku, line.price);
    },
    setQty(sku, qty) {
      const items = bag.items().map((i) => (i.sku === sku ? { ...i, qty } : i)).filter((i) => i.qty > 0);
      bag.write(items);
    },
    clear() {
      bag.write([]);
    },
    total() {
      return bag.items().reduce((s, i) => s + i.price * i.qty, 0);
    },
    count() {
      return bag.items().reduce((s, i) => s + i.qty, 0);
    },
  };
  let memory = null;

  const ICON_BOX = '<svg viewBox="0 0 28 28" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"><path d="M4 9l10-5 10 5v11l-10 5-10-5z"/><path d="M4 9l10 5 10-5M14 14v11"/></svg>';

  function lineHTML(i, editable = true) {
    const pic = i.img
      ? `<div class="line__img"><img src="${i.img}" alt=""></div>`
      : `<div class="line__img line__img--icon">${ICON_BOX}</div>`;
    const controls = editable
      ? `<div class="qty"><button type="button" data-qty="-1" data-sku="${i.sku}" aria-label="Уменьшить">−</button><span>${i.qty}</span><button type="button" data-qty="1" data-sku="${i.sku}" aria-label="Увеличить">+</button><button type="button" class="line__remove" data-remove="${i.sku}">Удалить</button></div>`
      : `<div class="line__meta">Количество: ${i.qty}</div>`;
    return `<div class="line">${pic}<div><div class="line__title">${i.title}</div>${i.meta ? `<div class="line__meta">${i.meta}</div>` : ""}${controls}</div><div class="line__price">${fmt(i.price * i.qty)}</div></div>`;
  }

  function renderBag() {
    const n = bag.count();
    $$("[data-bag-count]").forEach((el) => {
      el.textContent = String(n);
      el.hidden = n === 0;
    });
    const drawer = $("[data-drawer]");
    if (!drawer) return;
    const items = bag.items();
    drawer.innerHTML = `
      <div class="drawer__head"><h2>Корзина</h2><button class="drawer__close" type="button" data-close-bag aria-label="Закрыть"><svg viewBox="0 0 12 12" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><path d="M1 1l10 10M11 1L1 11"/></svg></button></div>
      <div class="drawer__body">${items.length ? items.map((i) => lineHTML(i)).join("") : '<p class="drawer__empty">В корзине пока пусто.<br><a href="buy.html" class="link-arrow">Выбрать Nokia 603</a></p>'}</div>
      ${items.length ? `<div class="drawer__foot"><div class="drawer__total"><span>Итого</span><span>${fmt(bag.total())}</span></div><p>Доставка Новой Почтой — бесплатно. Или ${fmt(Math.ceil(bag.total() / 6))}/мес. на 6 мес.</p><a class="btn btn--buy btn--lg btn--block" href="checkout.html">Оформить заказ</a></div>` : ""}`;
  }

  function openBag() {
    renderBag();
    document.body.classList.add("drawer-open");
    const d = $("[data-drawer]");
    if (d) {
      d.setAttribute("aria-hidden", "false");
      setTimeout(() => $(".drawer__close", d)?.focus(), 50);
    }
  }
  function closeBag() {
    document.body.classList.remove("drawer-open");
    $("[data-drawer]")?.setAttribute("aria-hidden", "true");
  }

  document.addEventListener("click", (e) => {
    const t = e.target.closest("[data-open-bag],[data-close-bag],[data-qty],[data-remove]");
    if (!t) return;
    if (t.matches("[data-open-bag]")) openBag();
    else if (t.matches("[data-close-bag]")) closeBag();
    else if (t.matches("[data-qty]")) {
      const item = bag.items().find((i) => i.sku === t.dataset.sku);
      if (item) bag.setQty(item.sku, Math.max(0, item.qty + Number(t.dataset.qty)));
      renderCheckoutSummary();
    } else if (t.matches("[data-remove]")) {
      bag.setQty(t.dataset.remove, 0);
      renderCheckoutSummary();
    }
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeBag();
  });

  let toastTimer;
  function toast(msg) {
    const el = $("[data-toast]");
    if (!el) return;
    el.textContent = msg;
    el.classList.add("is-on");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove("is-on"), 2400);
  }

  /* ---------------- local nav (mobile) ---------------- */
  const lnav = $(".lnav");
  const lnavToggle = $(".lnav__toggle");
  lnavToggle?.addEventListener("click", () => {
    const open = !lnav.classList.contains("is-open");
    lnav.classList.toggle("is-open", open);
    lnavToggle.setAttribute("aria-expanded", String(open));
  });
  $$(".lnav__links a").forEach((a) => a.addEventListener("click", () => lnav?.classList.remove("is-open")));

  /* ---------------- reveal on scroll ---------------- */
  const revealEls = $$(".reveal, .tile");
  if ("IntersectionObserver" in window && !reduceMotion) {
    const io = new IntersectionObserver(
      (entries) => entries.forEach((en) => {
        if (en.isIntersecting) {
          en.target.classList.add("in");
          io.unobserve(en.target);
        }
      }),
      { rootMargin: "0px 0px -8% 0px", threshold: 0.12 },
    );
    revealEls.forEach((el) => io.observe(el));
  } else {
    revealEls.forEach((el) => el.classList.add("in"));
  }
  const hero = $(".hero");
  if (hero) setTimeout(() => hero.classList.add("is-in"), 60);

  /* ---------------- highlights carousel ---------------- */
  const car = $("[data-carousel]");
  if (car) {
    const track = $(".hl__track", car);
    const slides = $$("[data-slide]", car);
    const dotsWrap = $("[data-dots]", car);
    const playBtn = $("[data-play]", car);
    const DURATION = 6000;
    let idx = 0;
    let playing = !reduceMotion;
    let start = performance.now();
    let visible = false;

    slides.forEach((_, i) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "hl__dot";
      b.setAttribute("role", "tab");
      b.setAttribute("aria-label", `Слайд ${i + 1}`);
      b.addEventListener("click", () => go(i, true));
      dotsWrap.appendChild(b);
    });
    const dots = $$(".hl__dot", dotsWrap);

    function mark(i) {
      idx = i;
      dots.forEach((d, k) => {
        d.classList.toggle("is-active", k === i);
        d.setAttribute("aria-selected", String(k === i));
        d.style.setProperty("--p", 0);
      });
    }
    function go(i, user = false) {
      const s = slides[i];
      track.scrollTo({ left: s.offsetLeft - parseFloat(getComputedStyle(track).paddingLeft), behavior: reduceMotion ? "auto" : "smooth" });
      mark(i);
      start = performance.now();
      if (user) setPlaying(false);
    }
    function setPlaying(p) {
      playing = p;
      start = performance.now();
      $("[data-icon-pause]", playBtn).toggleAttribute("hidden", !p);
      $("[data-icon-play]", playBtn).toggleAttribute("hidden", p);
      playBtn.setAttribute("aria-label", p ? "Пауза" : "Воспроизвести");
    }
    playBtn.addEventListener("click", () => setPlaying(!playing));
    let scrollT;
    track.addEventListener("scroll", () => {
      clearTimeout(scrollT);
      scrollT = setTimeout(() => {
        const left = track.scrollLeft;
        let best = 0;
        slides.forEach((s, k) => {
          if (Math.abs(s.offsetLeft - parseFloat(getComputedStyle(track).paddingLeft) - left) < Math.abs(slides[best].offsetLeft - parseFloat(getComputedStyle(track).paddingLeft) - left)) best = k;
        });
        if (best !== idx) {
          mark(best);
          start = performance.now();
        }
      }, 90);
    });
    new IntersectionObserver((en) => (visible = en[0].isIntersecting), { threshold: 0.35 }).observe(car);
    function tick(now) {
      if (playing && visible) {
        const p = Math.min(1, (now - start) / DURATION);
        dots[idx]?.style.setProperty("--p", p);
        if (p >= 1) go((idx + 1) % slides.length);
      } else if (!visible) {
        start = now - (parseFloat(dots[idx]?.style.getPropertyValue("--p")) || 0) * DURATION;
      }
      requestAnimationFrame(tick);
    }
    mark(0);
    setPlaying(playing);
    requestAnimationFrame(tick);
  }

  /* ---------------- colours showcase ---------------- */
  const colorsEl = $("[data-colors]");
  if (colorsEl) {
    $$(".swatch", colorsEl).forEach((sw) =>
      sw.addEventListener("click", () => {
        $$(".swatch", colorsEl).forEach((s) => s.setAttribute("aria-checked", String(s === sw)));
        $$("[data-color-img]", colorsEl).forEach((im) => im.classList.toggle("is-active", im.dataset.colorImg === sw.dataset.color));
        $("[data-color-name]", colorsEl).textContent = sw.dataset.name;
      }),
    );
  }

  /* ---------------- upgrade comparison ---------------- */
  // official Nokia spec sheets (Nokia Developer / nokia.com, 2011–2012); "modern" = typical 2026 flagship
  const COMPARE = {
    n5230: [
      { stat: "В 2,3 раза", title: "быстрее процессор", a: "1 ГГц", b: "434 МГц", text: "Меню, галерея и браузер открываются без пауз." },
      { stat: "В 4 раза", title: "больше оперативной памяти", a: "512 МБ", b: "128 МБ", text: "Приложения не закрываются, когда вы переключаетесь." },
      { stat: "Мультитач", title: "вместо резистивного экрана", a: "3,5″ ёмкостный", b: "3,2″ резистивный", text: "Лёгкие касания пальцем и масштаб двумя пальцами — без стилуса." },
      { stat: "Wi‑Fi и NFC", title: "которых у 5230 нет", a: "b/g/n, NFC, BT 3.0", b: "нет Wi‑Fi, BT 2.0", text: "Домашняя сеть и сопряжение одним касанием." },
    ],
    n5800: [
      { stat: "В 2,3 раза", title: "быстрее процессор", a: "1 ГГц", b: "434 МГц", text: "Belle работает плавно даже с десятком открытых приложений." },
      { stat: "В 4 раза", title: "больше оперативной памяти", a: "512 МБ", b: "128 МБ", text: "Музыка, браузер и карты одновременно." },
      { stat: "Мультитач", title: "вместо резистивного экрана", a: "3,5″ ёмкостный", b: "3,2″ резистивный", text: "Экран больше и отзывчивее — стилус больше не нужен." },
      { stat: "На 2,8 мм", title: "тоньше корпус", a: "12,7 мм", b: "15,5 мм", text: "При почти одинаковом весе — 109,6 г против 109 г." },
    ],
    c503: [
      { stat: "На 67%", title: "быстрее процессор", a: "1 ГГц", b: "600 МГц", text: "Заметно быстрее запуск камеры и приложений." },
      { stat: "В 4 раза", title: "больше оперативной памяти", a: "512 МБ", b: "128 МБ", text: "Больше вкладок и приложений одновременно." },
      { stat: "Мультитач", title: "вместо резистивного экрана", a: "3,5″ ёмкостный", b: "3,2″ резистивный", text: "Больше экран — и никаких нажатий с усилием." },
      { stat: "+300 мА·ч", title: "ёмкость аккумулятора", a: "1300 мА·ч", b: "1000 мА·ч", text: "Плюс NFC, Bluetooth 3.0 и Wi‑Fi n, которых у C5-03 нет." },
    ],
    c601: [
      { stat: "На 47%", title: "быстрее процессор", a: "1 ГГц", b: "680 МГц", text: "И новая Nokia Belle с живыми виджетами." },
      { stat: "Вдвое", title: "больше оперативной памяти", a: "512 МБ", b: "256 МБ", text: "Меньше перезапусков, больше открытых приложений." },
      { stat: "3,5″", title: "экран вместо 3,2″", a: "3,5″ ClearBlack", b: "3,2″ ClearBlack", text: "Та же технология ClearBlack — на большей диагонали." },
      { stat: "На 21 г", title: "легче", a: "109,6 г", b: "131 г", text: "И тоньше: 12,7 мм против 13,9 мм. Плюс NFC." },
    ],
    n8: [
      { stat: "На 47%", title: "быстрее процессор", a: "1 ГГц", b: "680 МГц", text: "Интерфейс отзывается заметно быстрее." },
      { stat: "Вдвое", title: "больше оперативной памяти", a: "512 МБ", b: "256 МБ", text: "Больше приложений в фоне без перезапуска." },
      { stat: "Съёмный", title: "аккумулятор", a: "BP‑3L, 1300 мА·ч", b: "BL‑4D, несъёмный", text: "Замена за десять секунд — без сервиса." },
      { stat: "На 25 г", title: "легче", a: "109,6 г", b: "135 г", text: "И NFC, которого у N8 нет." },
    ],
    modern: [
      { stat: "Разъём 3,5 мм", title: "на месте", a: "есть", b: "нет у большинства", text: "Любые проводные наушники — без переходника." },
      { stat: "Съёмный", title: "аккумулятор", a: "за 10 секунд", b: "только в сервисе", text: "Возите запасной и меняйте, когда удобно." },
      { stat: "FM‑радио", title: "без интернета", a: "есть, с RDS", b: "почти нигде", text: "Новости и музыка даже там, где нет связи." },
      { stat: "Почти вдвое", title: "легче", a: "109,6 г", b: "≈ 200 г", text: "Ощущается в кармане и в руке." },
    ],
  };
  const cmp = $("[data-compare]");
  if (cmp) {
    const sel = $("[data-compare-select]", cmp);
    const grid = $("[data-compare-grid]", cmp);
    const draw = () => {
      const name = sel.options[sel.selectedIndex].text;
      grid.classList.add("is-swapping");
      setTimeout(() => {
        grid.innerHTML = COMPARE[sel.value]
          .map(
            (c) => `<div class="tile in"><span class="t-stat">${c.stat}</span><span class="t-label" style="color:var(--ash);font-size:17px">${c.title}</span>
              <p class="t-body" style="margin-top:4px">${c.text}</p><div class="compare__versus t-body"><span><b>Nokia 603</b> — ${c.a}</span><span>${name} — ${c.b}</span></div></div>`,
          )
          .join("");
        grid.classList.remove("is-swapping");
      }, reduceMotion ? 0 : 180);
    };
    sel.addEventListener("change", draw);
    draw();
  }

  /* ---------------- buy configurator ---------------- */
  const buyEl = $("[data-buy]");
  if (buyEl) {
    const state = { condition: "new", body: "black", cover: "black", coverTouched: false, view: "front", extraCover: null, addons: new Set() };
    const params = new URLSearchParams(location.search);
    if (COLORS[params.get("cover")]) Object.assign(state, { cover: params.get("cover"), coverTouched: true, view: "back" });

    const stage = $("[data-stage]", buyEl);
    const setChecked = (group, value) =>
      $$(`[data-group="${group}"]`, buyEl).forEach((b) => b.setAttribute("aria-checked", String(b.dataset.value === value)));

    function showView(view) {
      state.view = view;
      const want = view === "front" ? img("hero", state.body) : img("back", state.cover);
      let el = $$("img", stage).find((i) => i.dataset.src === want);
      if (!el) {
        el = new Image();
        el.dataset.src = want;
        el.src = want;
        el.alt = view === "front" ? `Nokia 603, корпус «${COLORS[state.body].name}», вид спереди` : `Nokia 603, задняя панель «${COLORS[state.cover].name}»`;
        stage.appendChild(el);
      }
      stage.dataset.want = want;
      // only the latest request may win: a slow earlier load must not override the current view
      const activate = () => stage.dataset.want === want && $$("img", stage).forEach((i) => i.classList.toggle("is-active", i === el));
      el.complete ? activate() : el.addEventListener("load", activate, { once: true });
      $$("[data-view]", buyEl).forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.view === view)));
    }

    function update() {
      setChecked("condition", state.condition);
      setChecked("body", state.body);
      setChecked("cover", state.cover);
      $("[data-body-name]", buyEl).textContent = COLORS[state.body].name;
      $("[data-cover-name]", buyEl).textContent = COLORS[state.cover].name;
      $$("[data-addon]", buyEl).forEach((b) => b.setAttribute("aria-checked", String(state.addons.has(b.dataset.addon))));
      const extra = $("[data-extra-cover]", buyEl);
      extra.setAttribute("aria-checked", String(!!state.extraCover));
      $$("[data-extra-color]", buyEl).forEach((s) => s.setAttribute("aria-checked", String(s.dataset.extraColor === state.extraCover)));
      $("[data-extra-name]", buyEl).textContent = state.extraCover ? `цвет: ${COLORS[state.extraCover].name.toLowerCase()}` : "выберите цвет";
      const total = CONDITIONS[state.condition].price + (state.extraCover ? COVER_PRICE : 0) + [...state.addons].reduce((s, k) => s + ADDONS[k].price, 0);
      $("[data-total]", buyEl).textContent = fmt(total);
      $("[data-monthly]", buyEl).textContent = `или ${fmt(Math.ceil(total / 6))}/мес. на 6 мес. · доставка бесплатно`;
      $("[data-config]", buyEl).textContent = `${CONDITIONS[state.condition].name} · корпус ${COLORS[state.body].name.toLowerCase()} · панель ${COLORS[state.cover].panel}`;
      showView(state.view);
    }

    buyEl.addEventListener("click", (e) => {
      const b = e.target.closest("[data-group],[data-addon],[data-view],[data-extra-cover],[data-extra-color],[data-add-to-bag]");
      if (!b) return;
      if (b.dataset.group === "condition") state.condition = b.dataset.value;
      else if (b.dataset.group === "body") {
        state.body = b.dataset.value;
        if (!state.coverTouched) state.cover = b.dataset.value;
        state.view = "front";
      } else if (b.dataset.group === "cover") {
        state.cover = b.dataset.value;
        state.coverTouched = true;
        state.view = "back";
      } else if (b.dataset.addon) {
        state.addons.has(b.dataset.addon) ? state.addons.delete(b.dataset.addon) : state.addons.add(b.dataset.addon);
      } else if (b.dataset.view) state.view = b.dataset.view;
      else if (b.matches("[data-extra-color]")) {
        e.stopPropagation();
        state.extraCover = b.dataset.extraColor;
      } else if (b.matches("[data-extra-cover]")) state.extraCover = state.extraCover ? null : state.cover === "fuchsia" ? "green" : "fuchsia";
      else if (b.matches("[data-add-to-bag]")) {
        const c = CONDITIONS[state.condition];
        bag.add({
          sku: `n603-${state.condition}-${state.body}-${state.cover}`,
          title: "Nokia 603",
          meta: `${c.name} · корпус ${COLORS[state.body].name.toLowerCase()} · панель ${COLORS[state.cover].panel}`,
          price: c.price,
          img: img("hero", state.body),
        });
        if (state.extraCover) bag.add({ sku: `cover-${state.extraCover}`, title: "Задняя панель Nokia 603", meta: `Цвет: ${COLORS[state.extraCover].name.toLowerCase()}`, price: COVER_PRICE, img: img("back", state.extraCover) });
        state.addons.forEach((k) => bag.add({ sku: `addon-${k}`, title: ADDONS[k].title, meta: ADDONS[k].note, price: ADDONS[k].price }));
        toast("Добавлено в корзину");
        openBag();
        return;
      }
      update();
    });
    update();
  }

  /* ---------------- checkout ---------------- */
  function renderCheckoutSummary() {
    const box = $("[data-order-box]");
    if (!box) return;
    const items = bag.items();
    const total = bag.total();
    $("[data-order-lines]", box).innerHTML = items.length
      ? items.map((i) => lineHTML(i, false)).join("")
      : '<p class="muted" style="padding:18px 0">Корзина пуста. <a class="link-arrow" href="buy.html">Выбрать Nokia 603</a></p>';
    $("[data-order-sub]", box).textContent = fmt(total);
    $("[data-order-total]", box).textContent = fmt(total);
    $("[data-submit]")?.toggleAttribute("disabled", items.length === 0);
  }

  // Демо-витрина: заказы никуда не отправляются. TODO(canonical): подключить CRM и выставить false
  const DEMO_ORDERS = true;
  const form = $("[data-checkout]");
  if (form) {
    if (DEMO_ORDERS) $("[data-demo-note]")?.removeAttribute("hidden");
    renderCheckoutSummary();
    const deliveryFields = $("[data-delivery-fields]", form);
    const DELIVERY = {
      branch: '<div class="field"><label for="city">Город</label><input id="city" name="city" autocomplete="address-level2" required placeholder="Киев"><span class="field__err"></span></div><div class="field"><label for="branch">Номер отделения</label><input id="branch" name="branch" inputmode="numeric" required placeholder="Например, 25"><span class="field__err"></span></div>',
      locker: '<div class="field"><label for="city">Город</label><input id="city" name="city" autocomplete="address-level2" required placeholder="Киев"><span class="field__err"></span></div><div class="field"><label for="branch">Номер почтомата</label><input id="branch" name="branch" inputmode="numeric" required placeholder="Например, 5301"><span class="field__err"></span></div>',
      courier: '<div class="field"><label for="city">Город</label><input id="city" name="city" autocomplete="address-level2" required placeholder="Киев"><span class="field__err"></span></div><div class="field"><label for="address">Улица, дом, квартира</label><input id="address" name="address" autocomplete="street-address" required placeholder="ул. Крещатик, 1, кв. 1"><span class="field__err"></span></div>',
    };
    const syncDelivery = () => (deliveryFields.innerHTML = DELIVERY[form.elements.delivery.value]);
    $$('input[name="delivery"]', form).forEach((r) => r.addEventListener("change", syncDelivery));
    syncDelivery();

    const phone = form.elements.phone;
    phone.addEventListener("input", () => {
      let d = phone.value.replace(/\D/g, "");
      if (d.startsWith("0")) d = "38" + d;
      if (!d.startsWith("380")) d = "380" + d.replace(/^3?8?0?/, "");
      d = d.slice(0, 12);
      const p = [d.slice(0, 3), d.slice(3, 5), d.slice(5, 8), d.slice(8, 10), d.slice(10, 12)];
      phone.value = "+" + p[0] + (p[1] ? ` (${p[1]}` : "") + (p[1]?.length === 2 ? ")" : "") + (p[2] ? ` ${p[2]}` : "") + (p[3] ? `-${p[3]}` : "") + (p[4] ? `-${p[4]}` : "");
    });

    const err = (el, msg) => {
      const f = el.closest(".field");
      f.classList.toggle("is-invalid", !!msg);
      $(".field__err", f).textContent = msg || "";
      return !msg;
    };
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      let ok = true;
      $$("input[required], select[required]", form).forEach((el) => (ok = err(el, el.value.trim() ? "" : "Заполните поле") && ok));
      if (phone.value.replace(/\D/g, "").length !== 12) ok = err(phone, "Номер в формате +380 (XX) XXX-XX-XX") && ok;
      const email = form.elements.email;
      if (email.value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value)) ok = err(email, "Проверьте адрес почты") && ok;
      if (!ok) {
        $(".is-invalid input, .is-invalid select", form)?.focus();
        console.warn("[checkout] validation failed");
        return;
      }
      const order = {
        id: "N603-" + Math.random().toString(36).slice(2, 8).toUpperCase(),
        items: bag.items(),
        total: bag.total(),
        customer: Object.fromEntries(new FormData(form)),
        createdAt: new Date().toISOString(),
      };
      // TODO(canonical): отправить заказ в CRM/бэкенд магазина и получить номер оттуда — сейчас статичная витрина
      console.info("[checkout] order placed", order.id, order.total, order.items.length);
      bag.clear();
      const pay = { cod: "оплата при получении", card: "ссылку на онлайн-оплату пришлём в SMS", parts: "условия оплаты частями пришлём в SMS" }[order.customer.payment];
      $("[data-checkout-wrap]").innerHTML = `<div class="success"><div class="success__icon"><svg viewBox="0 0 34 34" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M8 17.5l6 6L26 11"/></svg></div>
        <h1 class="t-h2">${DEMO_ORDERS ? "Заказ сформирован." : "Спасибо, заказ принят."}</h1><p class="t-lead" style="margin:18px auto 8px;max-width:620px">Номер заказа <strong>${order.id}</strong> на сумму <strong>${fmt(order.total)}</strong>. ${DEMO_ORDERS ? "Это демо-витрина: заказ никуда не отправлен, и звонка не будет." : `Мы позвоним в течение 30 минут, чтобы подтвердить заказ; ${pay}.`}</p>
        <p class="muted t-body">${DEMO_ORDERS ? "В рабочей версии здесь будет подтверждение магазина." : "Отправка — в день подтверждения, доставка Новой Почтой обычно 1–2 дня."}</p><p style="margin-top:28px"><a class="btn btn--outline btn--lg" href="index.html">На главную</a></p></div>`;
      window.scrollTo({ top: 0, behavior: reduceMotion ? "auto" : "smooth" });
    });
  }

  renderBag();
  window.addEventListener("storage", (e) => e.key === BAG_KEY && (renderBag(), renderCheckoutSummary()));
})();
