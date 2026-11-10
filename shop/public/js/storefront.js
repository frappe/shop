(function () {
	// Set by Shop when the storefront is served under a route prefix, e.g. "/store".
	const base = window.shop_route_prefix || "";
	// Frappe's translation when the page has it
	const __ =
		window.__ || ((text, values) => text.replace(/\{(\d+)\}/g, (match, index) => (values && values[index] != null ? values[index] : match)));
	const state = {
		product: window.page_data && window.page_data.product,
		selection: {},
		cart: (window.page_data && window.page_data.cart) || null,
	};

	function esc(value) {
		const div = document.createElement("div");
		div.textContent = value == null ? "" : String(value);
		return div.innerHTML;
	}

	const GENERIC_ERROR = __("Something went wrong. Please try again.");

	async function call(method, args) {
		let response;
		try {
			response = await fetch(`/api/method/${method}`, {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
					"X-Frappe-CSRF-Token": (window.frappe && window.frappe.csrf_token) || "",
				},
				body: JSON.stringify(args || {}),
			});
		} catch (e) {
			throw new Error(__("We couldn't reach the store. Check your connection and try again."));
		}
		let body = {};
		try {
			body = await response.json();
		} catch (e) {
			if (!response.ok) throw new Error(GENERIC_ERROR);
		}
		if (!response.ok) throw new Error(serverMessage(body));
		return body.message;
	}

	function serverMessage(body) {
		try {
			const messages = JSON.parse(body._server_messages || "[]");
			if (messages.length) return JSON.parse(messages[0]).message.replace(/<[^>]+>/g, "");
		} catch (e) {}
		return GENERIC_ERROR;
	}

	// the error box of the form in use, else the page's
	function errorBox(scope) {
		return (scope && scope.querySelector('[data-shop="error"]')) || document.querySelector('[data-shop="error"]');
	}

	function showError(message, scope) {
		const target = errorBox(scope);
		if (target) {
			target.textContent = message;
			target.style.display = "block";
			target.scrollIntoView({ block: "nearest", behavior: "smooth" });
		} else {
			alert(message);
		}
	}

	function hideError(scope) {
		const target = errorBox(scope);
		if (target) target.style.display = "none";
	}

	function updateCartCount(count) {
		document.querySelectorAll('[data-shop="cart-count"]').forEach((el) => {
			el.textContent = count;
			el.dataset.empty = count ? "false" : "true";
		});
	}

	async function refreshCartCount() {
		if (!document.querySelector('[data-shop="cart-count"]')) return;
		if (window.page_data && window.page_data.cart) {
			updateCartCount(window.page_data.cart.item_count || 0);
			return;
		}
		try {
			const cart = await call("shop.storefront.cart.get_cart");
			updateCartCount(cart.item_count || 0);
		} catch (e) {}
	}

	// how many the shopper chose on the product page; null when it isn't a quantity. A product card
	// adds one.
	function chosenQty(button) {
		const input = document.querySelector('[data-shop="pdp-qty"]');
		if (!input || (button && button.closest(".product-card"))) return 1;
		const qty = parseFloat(input.value);
		if (qty > 0) return qty;
		showError(__("Enter how many you want."));
		input.focus();
		return null;
	}

	async function addToCart(button) {
		const itemCode = button.dataset.itemCode;
		const qty = chosenQty(button);
		if (!itemCode || qty === null) return;
		button.disabled = true;
		const label = button.textContent;
		try {
			const cart = await call("shop.storefront.cart.add_item", { item_code: itemCode, qty: qty });
			updateCartCount(cart.item_count || 0);
			if (drawerElement()) {
				renderDrawer(cart);
				openDrawer();
			} else {
				button.textContent = button.dataset.addedLabel || "Added";
				setTimeout(() => (button.textContent = label), 1500);
			}
		} catch (error) {
			showError(error.message);
		} finally {
			button.disabled = false;
		}
	}

	function drawerElement() {
		return document.querySelector('[data-shop="cart-drawer"]');
	}

	function openDrawer() {
		const drawer = drawerElement();
		if (!drawer) return false;
		drawer.dataset.open = "true";
		document.documentElement.style.overflow = "hidden";
		return true;
	}

	function closeDrawer() {
		const drawer = drawerElement();
		if (!drawer) return;
		drawer.dataset.open = "false";
		document.documentElement.style.overflow = "";
	}

	async function toggleDrawer() {
		try {
			renderDrawer(await call("shop.storefront.cart.get_cart"));
			openDrawer();
		} catch (error) {
			window.location.href = base + "/cart";
		}
	}

	function renderDrawer(cart) {
		state.cart = cart;
		updateCartCount(cart.item_count || 0);
		const drawer = drawerElement();
		if (!drawer) return;
		const total = drawer.querySelector('[data-shop="drawer-total"]');
		if (total) total.textContent = cart.formatted_total || "";
		const list = drawer.querySelector('[data-shop="drawer-items"]');
		if (!list) return;
		if (!cart.items.length) {
			list.innerHTML = '<p class="drawer-empty">Your cart is empty.</p>';
			return;
		}
		list.innerHTML = cart.items
			.map(
				(item) => `
			<div class="drawer-item">
				<img class="drawer-thumb" src="${esc(item.image || "")}" alt="" loading="lazy">
				<div class="drawer-info">
					<a class="drawer-name" href="${base}/product/${esc(item.slug || "")}">${esc(item.product_name || item.item_code)}</a>
					<span class="drawer-rate">${esc(item.formatted_rate || "")}</span>
					<div class="drawer-qty">
						<button type="button" data-drawer-step="-1" data-item-code="${esc(item.item_code)}" aria-label="Decrease quantity">&minus;</button>
						<input type="number" data-drawer-qty data-item-code="${esc(item.item_code)}" value="${esc(item.qty)}" min="0" step="any" inputmode="decimal" aria-label="${esc(__("Quantity"))}">
						<button type="button" data-drawer-step="1" data-item-code="${esc(item.item_code)}" aria-label="Increase quantity">+</button>
						<button type="button" class="drawer-remove" data-drawer-step="0" data-item-code="${esc(item.item_code)}">Remove</button>
					</div>
				</div>
				<span class="drawer-amount">${esc(item.formatted_amount || "")}</span>
			</div>`
			)
			.join("");
	}

	async function drawerStep(itemCode, step) {
		const row = state.cart && state.cart.items.find((item) => item.item_code === itemCode);
		await drawerQty(itemCode, step === 0 ? 0 : Math.max((row ? row.qty : 1) + step, 0));
	}

	async function drawerQty(itemCode, qty) {
		try {
			const cart = await call("shop.storefront.cart.set_qty", { item_code: itemCode, qty: qty });
			renderDrawer(cart);
			cartChanged();
		} catch (error) {
			if (state.cart) renderDrawer(state.cart);
			showError(error.message);
		}
	}

	// on the checkout page a changed cart has a new total
	function cartChanged() {
		if (!checkoutForm()) return;
		checkout.quote = null;
		scheduleQuote(0);
	}

	async function setQty(itemCode, qty) {
		try {
			await call("shop.storefront.cart.set_qty", { item_code: itemCode, qty: qty });
			window.location.reload();
			return true;
		} catch (error) {
			showError(error.message);
			return false;
		}
	}

	// a quantity typed in the cart or the drawer: none removes the line; what isn't a quantity is put back
	function typedQty(input, current) {
		const qty = input.value.trim() === "" ? NaN : parseFloat(input.value);
		if (qty >= 0) return qty;
		input.value = current;
		showError(__("Enter how many you want."));
		return null;
	}

	function rowQty(itemCode) {
		const row = window.page_data && window.page_data.cart
			? window.page_data.cart.items.find((item) => item.item_code === itemCode)
			: null;
		return row ? row.qty : 1;
	}

	function mainImage() {
		return document.querySelector('[data-shop="main-image"]');
	}

	function showImage(src) {
		const target = mainImage();
		if (!target || !src || target.getAttribute("src") === src) return;
		target.setAttribute("src", src);
		document.querySelectorAll('[data-shop="thumb"]').forEach((thumb) => {
			thumb.dataset.selected = thumb.dataset.image === src ? "true" : "false";
		});
	}

	function initGallery() {
		const first = document.querySelector('[data-shop="thumb"]');
		if (first) first.dataset.selected = "true";
	}

	// out of stock: the shopper can ask to be told when it's back (not when it isn't sold online)
	function syncStockAlert(item) {
		// a variant names its item; the product page's own data names the one it sells
		const code = item.item_code || item.buy_item_code;
		document.querySelectorAll('[data-shop="stock-alert"]').forEach((form) => {
			form.hidden = item.purchasable !== false || item.stock_state !== "out" || !code;
			if (code && form.dataset.itemCode !== code) {
				form.dataset.itemCode = code;
				const done = form.querySelector('[data-shop="stock-alert-done"]');
				if (done) done.hidden = true;
				form.querySelector(".stock-alert-row").hidden = false;
			}
		});
	}

	function initStockAlert() {
		document.querySelectorAll('[data-shop="stock-alert"]').forEach((form) => {
			form.addEventListener("submit", async (event) => {
				event.preventDefault();
				const input = form.querySelector('input[name="email"]');
				const button = form.querySelector('button[type="submit"]');
				const done = form.querySelector('[data-shop="stock-alert-done"]');
				if (!input.value.trim()) return input.focus();
				button.disabled = true;
				try {
					const result = await call("shop.storefront.product.alert_when_in_stock", {
						item_code: form.dataset.itemCode,
						email: input.value.trim(),
					});
					form.querySelector(".stock-alert-row").hidden = true;
					done.textContent = result.message;
					done.hidden = false;
				} catch (error) {
					showError(error.message);
				} finally {
					button.disabled = false;
				}
			});
		});
	}

	function syncAvailability(item) {
		syncStockAlert(item);
		// the product's own buttons, not those on the product cards listed below it
		const buttons = [...document.querySelectorAll('[data-shop="add-to-cart"], [data-shop="buy-now"]')].filter(
			(button) => !button.closest(".product-card")
		);
		buttons.forEach((button) => {
			if (item.item_code) button.dataset.itemCode = item.item_code;
			button.disabled = !item.purchasable;
			if (!item.purchasable) button.textContent = item.stock_status || button.dataset.outOfStockLabel;
			else if (button.dataset.label) button.textContent = button.dataset.label;
		});
		document.querySelectorAll('[data-shop="pdp-qty"]').forEach((input) => {
			input.disabled = !item.purchasable;
		});
		document.querySelectorAll('[data-shop="stock-status"]').forEach((line) => {
			line.dataset.stockState = item.stock_state || "";
			const text = line.querySelector('[data-shop="stock-status-text"]');
			if (text) text.textContent = item.stock_status || "";
		});
		// stock at each location the store shows (ready-made, escaped, by the server)
		document.querySelectorAll('[data-shop="stock-locations"]').forEach((list) => {
			list.innerHTML = item.stock_locations_html || "";
			list.hidden = !item.stock_locations_html;
		});
		// where the variant can be sent (escaped by the server)
		document.querySelectorAll('[data-shop="shipping-note"]').forEach((note) => {
			note.innerHTML = item.shipping_note || "";
			note.hidden = !item.shipping_note;
		});
	}

	function initVariantPicker() {
		const product = state.product;
		if (product && !product.has_variants && product.stock_status) syncAvailability(product);
		if (!product || !product.has_variants) return;
		const defaultVariant = product.variants.find(
			(variant) => variant.item_code === product.default_item_code
		);
		if (defaultVariant) state.selection = Object.assign({}, defaultVariant.attributes);
		syncVariantUI();
	}

	function selectOption(button) {
		state.selection[button.dataset.attribute] = button.dataset.value;
		syncVariantUI();
	}

	function selectedVariant() {
		const product = state.product;
		if (!product) return null;
		return product.variants.find((variant) =>
			Object.entries(variant.attributes).every(
				([attribute, value]) => state.selection[attribute] === value
			)
		);
	}

	// whether picking this value, with the other options as they are, gives a variant that can be bought
	function optionAvailable(attribute, value) {
		const wanted = Object.assign({}, state.selection, { [attribute]: value });
		return state.product.variants.some(
			(variant) =>
				variant.purchasable &&
				Object.entries(variant.attributes).every(([name, picked]) => wanted[name] === picked)
		);
	}

	function syncVariantUI() {
		document.querySelectorAll('[data-shop="variant-option"]').forEach((button) => {
			const selected = state.selection[button.dataset.attribute] === button.dataset.value;
			button.dataset.selected = selected ? "true" : "false";
			button.setAttribute("aria-pressed", selected ? "true" : "false");
			button.dataset.available = optionAvailable(button.dataset.attribute, button.dataset.value) ? "true" : "false";
		});
		const variant = selectedVariant();
		const prices = document.querySelectorAll(
			'[data-shop="pdp-price"], [data-shop="pdp-price-note"], [data-shop="pdp-compare-at"]'
		);
		if (!variant) {
			// a combination the store doesn't sell: nothing of another variant stays on the page
			syncAvailability({
				purchasable: false,
				stock_status: state.product.unavailable_label,
				stock_state: "unavailable",
			});
			prices.forEach((price) => (price.hidden = true));
			syncSavings({});
			return;
		}
		prices.forEach((price) => (price.hidden = false));
		// the "was" price only beside a variant that sells below it
		document.querySelectorAll('[data-shop="pdp-compare-at"]').forEach((price) => {
			price.hidden = !variant.formatted_savings;
		});
		syncAvailability(variant);
		if (variant.formatted_price) {
			document.querySelectorAll('[data-shop="pdp-price"]').forEach((price) => {
				price.textContent = variant.formatted_price;
			});
			document.querySelectorAll('[data-shop="pdp-price-note"]').forEach((note) => {
				note.textContent = variant.price_note || "";
			});
		}
		syncSavings(variant);
		if (variant.image) showImage(variant.image);
	}

	function syncSavings(variant) {
		const savings = document.querySelector('[data-shop="pdp-savings"]');
		if (savings) {
			savings.hidden = !variant.formatted_savings;
			const amount = savings.querySelectorAll("span")[1];
			if (amount && variant.formatted_savings) amount.textContent = variant.formatted_savings;
		}
		const badge = document.querySelector('[data-shop="pdp-discount"]');
		if (badge) {
			badge.hidden = !variant.discount_pct;
			const pct = badge.querySelector("span");
			if (pct && variant.discount_pct) pct.textContent = variant.discount_pct;
		}
	}

	async function buyNow(button) {
		const itemCode = button.dataset.itemCode;
		const qty = chosenQty();
		if (!itemCode || qty === null) return;
		button.disabled = true;
		try {
			await call("shop.storefront.cart.add_item", { item_code: itemCode, qty: qty });
			window.location.href = base + "/checkout";
		} catch (error) {
			showError(error.message);
			button.disabled = false;
		}
	}

	// ---- checkout -------------------------------------------------------------
	// A theme opts in by placing these hooks in the checkout form:
	// [data-shop="shipping-options"], [data-shop="checkout-totals"], [data-shop="bank-currency"],
	// [data-shop="payment-fee"][data-method], and inputs named accept_terms / business_buyer.
	const checkout = { quote: null, timer: null, seq: 0, submitting: false };
	const ADDRESS_FIELDS = ["address_line1", "address_line2", "city", "state", "country", "pincode"];

	function checkoutForm() {
		return document.querySelector('[data-shop="checkout-form"]');
	}

	function formAddress(form) {
		const data = new FormData(form);
		const address = {};
		ADDRESS_FIELDS.forEach((field) => (address[field] = (data.get(field) || "").trim()));
		return address;
	}

	// one service, or one per parcel when the order is sent from more than one warehouse
	function shippingChoice(form) {
		const picks = [...form.querySelectorAll('input[name^="shipping_option:"]:checked')];
		if (picks.length) {
			return JSON.stringify(Object.fromEntries(picks.map((input) => [input.name.slice("shipping_option:".length), input.value])));
		}
		const picked = new FormData(form).get("shipping_option");
		if (picked) return picked;
		// a choice restored before the quote has drawn its services
		const held = Object.entries(checkout.heldChoices || {});
		const parcels = held.filter(([name]) => name.startsWith("shipping_option:"));
		if (parcels.length) {
			return JSON.stringify(Object.fromEntries(parcels.map(([name, value]) => [name.slice("shipping_option:".length), value])));
		}
		return (checkout.heldChoices || {}).shipping_option || undefined;
	}

	// check the held choices among the services the quote drew, once
	function applyHeldChoices(form) {
		Object.entries(checkout.heldChoices || {}).forEach(([name, value]) => {
			const radio = [...form.querySelectorAll(`input[type="radio"][name="${CSS.escape(name)}"]`)].find(
				(field) => field.value === value
			);
			if (radio) {
				radio.checked = true;
				delete checkout.heldChoices[name];
			}
		});
	}

	function shippingOptionsHtml(options, name) {
		return options
			.map(
				(option) => `<label class="checkout-option"><input type="radio" name="${esc(name)}" value="${esc(option.id)}"${option.selected ? " checked" : ""}>
						<span class="checkout-option-label">${esc(option.label)}${option.eta ? ` <small>${esc(option.eta)}</small>` : ""}</span>
						<span class="checkout-option-price">${esc(option.formatted)}</span></label>`
			)
			.join("");
	}

	function checkoutChoice(form) {
		const data = new FormData(form);
		const currency = form.querySelector('select[name="currency"]');
		const method = data.get("payment_method") || undefined;
		return {
			shipping_option: shippingChoice(form),
			// an international transfer is chosen under bank transfer, as where the money comes from
			payment_method: method === "bank" && data.get("bank_route") ? data.get("bank_route") : method,
			// until the shopper picks one, the store suggests their own currency
			currency: currency && currency.dataset.chosen ? data.get("currency") : undefined,
		};
	}

	function scheduleQuote(delay) {
		const form = checkoutForm();
		if (!form || !document.querySelector('[data-shop="checkout-totals"]')) return;
		// what changed may change the total: an order isn't placed at the old one
		checkout.quote = null;
		// a quote already on its way is for what was there before
		checkout.seq++;
		clearTimeout(checkout.timer);
		checkout.timer = setTimeout(() => requestQuote(form), delay == null ? 450 : delay);
	}

	async function requestQuote(form) {
		const seq = ++checkout.seq;
		const totalsBox = document.querySelector('[data-shop="checkout-totals"]');
		totalsBox && totalsBox.setAttribute("aria-busy", "true");
		try {
			const quote = await call("shop.storefront.checkout.quote", { address: formAddress(form), ...checkoutChoice(form) });
			if (seq !== checkout.seq) return null;
			checkout.quote = quote;
			hideError(form);
			renderQuote(form, quote);
			return quote;
		} catch (error) {
			if (seq === checkout.seq) {
				checkout.quote = null;
				showError(error.message, form);
			}
			return null;
		} finally {
			totalsBox && totalsBox.removeAttribute("aria-busy");
		}
	}

	function renderQuote(form, quote) {
		const options = form.querySelector('[data-shop="shipping-options"]');
		if (options) {
			const hints = (quote.shipping_messages || []).map((m) => `<p class="checkout-hint">${esc(m)}</p>`).join("");
			let html;
			if (quote.shipping_pending) {
				html = `<p class="checkout-hint">${esc(__("Enter your address to see shipping options."))}</p>`;
			} else if ((quote.shipping_groups || []).length) {
				html =
					quote.shipping_groups
						.map(
							(group) => `<div class="checkout-parcel"><p class="checkout-hint"><strong>${esc(group.label)}</strong> · ${esc(group.items)}</p>
							${group.options.length ? shippingOptionsHtml(group.options, `shipping_option:${group.key}`) : `<div class="checkout-warning" role="alert"><p>${esc(__("We can't send this parcel to this address."))}</p></div>`}</div>`
						)
						.join("") + hints;
			} else if (!quote.shipping_options.length) {
				const reasons = (quote.shipping_messages || []).map((m) => `<p>${esc(m)}</p>`).join("");
				html = `<div class="checkout-warning" role="alert">${reasons || `<p>${esc(__("We can't ship to this address. Check it, or contact us."))}</p>`}</div>`;
			} else {
				html = shippingOptionsHtml(quote.shipping_options, "shipping_option") + hints;
			}
			// drawn again only when it changed, and the shopper keeps their place in it
			if (options.dataset.rendered !== html) {
				const focused = options.contains(document.activeElement) ? document.activeElement : null;
				options.innerHTML = html;
				options.dataset.rendered = html;
				if (focused && focused.name) {
					const again = [...options.querySelectorAll(`[name="${CSS.escape(focused.name)}"]`)].find(
						(field) => field.value === focused.value
					);
					if (again) again.focus();
				}
			}
			applyHeldChoices(form);
		}
		form.querySelectorAll('[data-shop="payment-fee"]').forEach((note) => {
			const method = (quote.payment_methods || []).find((m) => m.method === note.dataset.method);
			note.textContent = (method && method.fee_note) || "";
		});
		const bank = form.querySelector('[data-shop="bank-currency"]');
		if (bank) {
			const byBank = ["bank", "swift"].includes(quote.payment_method);
			const currencies = quote.bank_currencies || [];
			const routes = quote.bank_routes || [];
			const select = bank.querySelector('select[name="currency"]');
			if (select) {
				const options = currencies.map((c) => `<option value="${esc(c.currency)}">${esc(c.label)}</option>`).join("");
				if (select.dataset.options !== options) {
					select.innerHTML = options;
					select.dataset.options = options;
				}
				if (quote.currency && byBank) select.value = quote.currency;
			}
			const currencyChoice = bank.querySelector('[data-shop="bank-currency-choice"]');
			if (currencyChoice) currencyChoice.hidden = currencies.length < 2;
			const route = bank.querySelector('select[name="bank_route"]');
			if (route) {
				route.innerHTML = routes.map((r) => `<option value="${esc(r.method)}">${esc(r.label)}</option>`).join("");
				route.value = quote.payment_method;
				// until the shopper says where they pay from, go by where the order is going
				const suggested = quote.suggested_bank_method;
				if (byBank && !route.dataset.chosen && suggested && suggested !== quote.payment_method && routes.some((r) => r.method === suggested)) {
					route.value = suggested;
					scheduleQuote(0);
				}
			}
			const routeChoice = bank.querySelector('[data-shop="bank-route"]');
			if (routeChoice) routeChoice.hidden = routes.length < 2;
			bank.hidden = !byBank || (currencies.length < 2 && routes.length < 2);
		}
		(quote.items || []).forEach((item) => {
			document
				.querySelectorAll(`[data-shop="line-amount"][data-item-code="${CSS.escape(item.item_code)}"]`)
				.forEach((amount) => (amount.textContent = item.formatted_amount));
		});
		const totalsBox = document.querySelector('[data-shop="checkout-totals"]');
		if (totalsBox) {
			const lines = quote.lines
				.map((line) => `<div class="checkout-line" data-kind="${esc(line.kind)}"><span>${esc(line.label)}</span><span>${esc(line.formatted)}</span></div>`)
				.join("");
			const notes = (quote.notes || []).map((note) => `<p class="checkout-note">${esc(note)}</p>`).join("");
			totalsBox.innerHTML = `${lines}<div class="checkout-line checkout-total"><span>Total</span><span data-shop="checkout-total">${esc(quote.formatted_total)} ${esc(quote.currency)}</span></div>${notes}`;
		}
		const submit = form.querySelector('[type="submit"]');
		if (submit) submit.disabled = !quote.can_ship || checkout.submitting;
		syncPaymentUI();
	}

	async function submitCheckout(form) {
		if (checkout.submitting) return;
		const data = new FormData(form);
		const submit = form.querySelector('[type="submit"]');
		const terms = form.querySelector('[name="accept_terms"]');
		if (terms && !terms.checked) {
			showError(__("Please accept the terms and conditions."), form);
			terms.focus();
			return;
		}
		clearTimeout(checkout.timer);
		checkout.submitting = true;
		if (submit) submit.disabled = true;
		// the order is placed at the total the shopper is shown, worked out now if it isn't yet
		const quote = checkout.quote || (await requestQuote(form));
		checkout.seq++;
		if (!quote) {
			checkout.submitting = false;
			if (submit) submit.disabled = false;
			return;
		}
		try {
			const result = await call("shop.storefront.checkout.place_order", {
				customer: {
					email: data.get("email"),
					full_name: data.get("full_name"),
					phone: data.get("phone"),
				},
				address: formAddress(form),
				...checkoutChoice(form),
				accept_terms: terms && terms.checked ? 1 : 0,
				business_buyer: data.get("business_buyer") ? 1 : 0,
				po_no: data.get("po_no") || undefined,
				order_note: data.get("order_note") || undefined,
				expected_total: quote.total,
			});
			window.location.href = result.payment_url || result.confirmation_url;
		} catch (error) {
			checkout.submitting = false;
			showError(error.message, form);
			if (submit) submit.disabled = false;
			scheduleQuote(0);
		}
	}

	async function submitAccountForm(form, method, collect) {
		const submit = form.querySelector('[type="submit"]');
		const done = form.parentElement.querySelector('[data-shop="form-done"]');
		if (submit) submit.disabled = true;
		try {
			const result = await call(method, collect(new FormData(form)));
			form.hidden = true;
			if (done) {
				done.textContent = result.message;
				done.hidden = false;
			}
		} catch (error) {
			showError(error.message, form);
			if (submit) submit.disabled = false;
		}
	}

	async function acceptQuote(form) {
		const data = new FormData(form);
		const submit = form.querySelector('[type="submit"]');
		if (submit) submit.disabled = true;
		try {
			const result = await call("shop.storefront.quotes.accept_quote", {
				name: form.dataset.quote,
				token: form.dataset.token,
				payment_method: data.get("payment_method"),
				accept_terms: data.get("accept_terms") ? 1 : 0,
				business_buyer: data.get("business_buyer") ? 1 : 0,
			});
			window.location.href = result.redirect;
		} catch (error) {
			showError(error.message, form);
			if (submit) submit.disabled = false;
		}
	}

	async function submitQuoteRequest(button) {
		const form = checkoutForm();
		if (!form) return;
		// a quote needs contact and address details, not the terms (those come with the order)
		const missing = [...form.querySelectorAll("[required]")].find(
			(input) => input.name !== "accept_terms" && !input.checkValidity()
		);
		if (missing) {
			missing.reportValidity();
			return;
		}
		const data = new FormData(form);
		button.disabled = true;
		try {
			const result = await call("shop.storefront.quotes.request_quote", {
				customer: { email: data.get("email"), full_name: data.get("full_name"), phone: data.get("phone") },
				address: formAddress(form),
				shipping_option: shippingChoice(form),
				message: data.get("quote_message") || "",
			});
			const done = document.querySelector('[data-shop="quote-done"]');
			if (done) {
				done.textContent = result.message + " (" + result.quote + ")";
				done.hidden = false;
			}
			button.hidden = true;
		} catch (error) {
			showError(error.message);
			button.disabled = false;
		}
	}

	function initCheckout() {
		const form = checkoutForm();
		if (!form) return;
		const country = form.querySelector('select[name="country"]');
		if (country) {
			const pageData = window.page_data || {};
			const wanted = (pageData.prefill && pageData.prefill.country) || pageData.default_country;
			if (wanted) country.value = wanted;
		}
		restoreCheckoutDraft(form);
		form.addEventListener("input", (event) => {
			if (ADDRESS_FIELDS.includes(event.target.name)) scheduleQuote();
		});
		form.addEventListener("change", (event) => {
			const name = event.target.name;
			if (name === "currency" || name === "bank_route") event.target.dataset.chosen = "1";
			if (["shipping_option", "payment_method", "currency", "bank_route", "country"].includes(name) || name.startsWith("shipping_option:")) scheduleQuote(0);
		});
		scheduleQuote(0);
	}

	document.addEventListener("click", (event) => {
		const stepper = event.target.closest("[data-drawer-step]");
		if (stepper) {
			drawerStep(stepper.dataset.itemCode, parseInt(stepper.dataset.drawerStep, 10));
			return;
		}
		const target = event.target.closest("[data-shop]");
		if (!target) return;
		const action = target.dataset.shop;
		if (action === "cart-toggle" && drawerElement()) {
			event.preventDefault();
			toggleDrawer();
		} else if (action === "drawer-close" || action === "drawer-backdrop") closeDrawer();
		else if (action === "coupon-remove") removeCoupon();
		else if (action === "sign-out") {
			event.preventDefault();
			signOut();
		}
		else if (action === "add-to-cart") addToCart(target);
		else if (action === "buy-now") buyNow(target);
		else if (action === "thumb") showImage(target.dataset.image);
		else if (action === "rating-star") selectRating(parseInt(target.dataset.value, 10));
		else if (action === "variant-option") selectOption(target);
		else if (action === "qty-inc") setQty(target.dataset.itemCode, rowQty(target.dataset.itemCode) + 1);
		else if (action === "qty-dec") setQty(target.dataset.itemCode, rowQty(target.dataset.itemCode) - 1);
		else if (action === "remove") setQty(target.dataset.itemCode, 0);
		else if (action === "request-quote") submitQuoteRequest(target);
		else if (action === "forgot-password") forgotPassword(target.closest("form"));
	});

	document.addEventListener("keydown", (event) => {
		if (event.key === "Escape") closeDrawer();
	});

	document.addEventListener("change", async (event) => {
		const input = event.target;
		if (input.matches('[data-shop="qty-input"]')) {
			const current = rowQty(input.dataset.itemCode);
			const qty = typedQty(input, current);
			if (qty !== null && !(await setQty(input.dataset.itemCode, qty))) input.value = current;
		} else if (input.matches("[data-drawer-qty]")) {
			const row = state.cart && state.cart.items.find((item) => item.item_code === input.dataset.itemCode);
			const qty = typedQty(input, row ? row.qty : 1);
			if (qty !== null) drawerQty(input.dataset.itemCode, qty);
		}
	});

	document.addEventListener("submit", (event) => {
		const form = event.target.closest("[data-shop]");
		if (!form) return;
		if (form.dataset.shop === "checkout-form") {
			event.preventDefault();
			submitCheckout(form);
		} else if (form.dataset.shop === "signin-form") {
			event.preventDefault();
			signIn(form);
		} else if (form.dataset.shop === "register-form") {
			event.preventDefault();
			submitAccountForm(form, "shop.storefront.accounts.register", (data) => ({
				full_name: data.get("full_name"),
				email: data.get("email"),
				accept_terms: data.get("accept_terms") ? 1 : 0,
			}));
		} else if (form.dataset.shop === "trade-form") {
			event.preventDefault();
			submitAccountForm(form, "shop.storefront.accounts.apply_trade", (data) => ({
				application: Object.fromEntries(
					["company_name", "company_number", "tax_id", "industry", "website", "country", "message",
					 "contact_name", "email", "phone", "address_line1", "address_line2", "city", "state", "pincode"]
						.map((key) => [key, data.get(key) || ""])
				),
				accept_terms: data.get("accept_terms") ? 1 : 0,
			}));
		} else if (form.dataset.shop === "quote-form") {
			event.preventDefault();
			acceptQuote(form);
		} else if (form.dataset.shop === "review-form") {
			event.preventDefault();
			submitReview(form);
		} else if (form.dataset.shop === "coupon-form") {
			event.preventDefault();
			applyCoupon(form);
		} else if (form.dataset.shop === "return-form") {
			event.preventDefault();
			submitReturn(form);
		} else if (form.dataset.shop === "search-form") {
			event.preventDefault();
			const term = form.querySelector('[name="search"]');
			window.location.href = base + "/products?search=" + encodeURIComponent(term ? term.value : "");
		}
	});

	function loggedIn() {
		const match = document.cookie.match(/(?:^|; )user_id=([^;]*)/);
		return !!match && decodeURIComponent(match[1]) !== "Guest";
	}

	function initReviewForm() {
		const form = document.querySelector('[data-shop="review-form"]');
		const prompt = document.querySelector('[data-shop="review-signin"]');
		if (!form) return;
		if (loggedIn()) {
			form.style.display = "flex";
			if (prompt) prompt.style.display = "none";
		} else if (prompt) {
			prompt.setAttribute(
				"href",
				base + "/account/signin?redirect-to=" + encodeURIComponent(window.location.pathname)
			);
		}
	}

	function selectRating(value) {
		state.reviewRating = value;
		document.querySelectorAll('[data-shop="rating-star"]').forEach((star) => {
			star.dataset.selected = parseInt(star.dataset.value, 10) <= value ? "true" : "false";
		});
	}

	async function submitReview(form) {
		if (!state.reviewRating) {
			showError(__("Pick a star rating first."), form);
			return;
		}
		const data = new FormData(form);
		const submit = form.querySelector('[type="submit"]');
		if (submit) submit.disabled = true;
		try {
			await call("shop.storefront.reviews.add_review", {
				product: window.page_data.product.name,
				rating: state.reviewRating,
				title: data.get("title"),
				review: data.get("review"),
			});
			const thanks = document.createElement("p");
			thanks.className = "form-done";
			thanks.textContent = __("Thank you for your review.");
			form.replaceWith(thanks);
		} catch (error) {
			showError(error.message, form);
			if (submit) submit.disabled = false;
		}
	}

	// what the shopper typed at checkout is kept over the reload a coupon change makes
	const DRAFT_KEY = "shop_checkout_draft";

	function saveCheckoutDraft() {
		const form = checkoutForm();
		if (!form) return;
		const draft = {};
		form.querySelectorAll("input[name], select[name], textarea[name]").forEach((field) => {
			if (field.type === "radio" || field.type === "checkbox") {
				if (field.checked) draft[field.name] = field.type === "checkbox" ? true : field.value;
			} else if (field.value) draft[field.name] = field.value;
		});
		try {
			sessionStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
		} catch (error) {
			// private windows may refuse storage; the shopper retypes
		}
	}

	function restoreCheckoutDraft(form) {
		let draft = null;
		try {
			draft = JSON.parse(sessionStorage.getItem(DRAFT_KEY) || "null");
			sessionStorage.removeItem(DRAFT_KEY);
		} catch (error) {
			return;
		}
		if (!draft) return;
		checkout.heldChoices = {};
		Object.entries(draft).forEach(([name, value]) => {
			const fields = form.querySelectorAll(`[name="${CSS.escape(name)}"]`);
			// services are drawn by the first quote: their choice waits for it
			if (!fields.length && name.startsWith("shipping_option")) checkout.heldChoices[name] = value;
			fields.forEach((field) => {
				if (field.type === "radio") field.checked = field.value === value;
				else if (field.type === "checkbox") field.checked = !!value;
				else if (field.tagName === "SELECT" && !field.options.length) {
					// filled from the quote: hold the choice until the quote fills it
					field.innerHTML = `<option value="${esc(value)}"></option>`;
					field.value = value;
				} else field.value = value;
				if (name === "currency" || name === "bank_route") field.dataset.chosen = "1";
			});
		});
	}

	async function applyCoupon(form) {
		const input = form.querySelector('[name="code"]');
		if (!input || !input.value.trim()) return;
		const submit = form.querySelector('[type="submit"]');
		if (submit) submit.disabled = true;
		try {
			await call("shop.storefront.cart.apply_coupon", { code: input.value.trim() });
			saveCheckoutDraft();
			window.location.reload();
		} catch (error) {
			showError(error.message);
			if (submit) submit.disabled = false;
		}
	}

	// Frappe's own login and password reset, from the store's sign-in page
	async function signIn(form) {
		const data = new FormData(form);
		const submit = form.querySelector('[type="submit"]');
		const next = form.dataset.redirect || base + "/account/orders";
		hideError(form);
		if (submit) submit.disabled = true;
		let result;
		try {
			result = await call("login", { usr: data.get("email"), pwd: data.get("password") });
		} catch (error) {
			showError(__("That email and password don't match an account. Check them, or reset your password."), form);
			if (submit) submit.disabled = false;
			return;
		}
		// two-factor sign-in needs Frappe's own page
		if (result === undefined || (result && result.verification)) {
			window.location.href = "/login?redirect-to=" + encodeURIComponent(next);
			return;
		}
		window.location.href = next;
	}

	async function forgotPassword(form) {
		const email = form && form.querySelector('[name="email"]');
		if (!email || !email.value || !email.checkValidity()) {
			showError(__("Enter your email address first, then choose Forgot your password."), form);
			if (email) email.focus();
			return;
		}
		hideError(form);
		const done = form.parentElement.querySelector('[data-shop="form-done"]');
		try {
			await call("frappe.core.doctype.user.user.reset_password", { user: email.value });
			if (done) {
				done.textContent = __("If {0} has an account, we've emailed it a link to set a new password.").replace("{0}", email.value);
				done.hidden = false;
			}
		} catch (error) {
			showError(error.message, form);
		}
	}

	async function signOut() {
		try {
			await call("logout", {});
		} finally {
			window.location.href = base || "/";
		}
	}

	async function removeCoupon() {
		try {
			await call("shop.storefront.cart.remove_coupon", {});
			saveCheckoutDraft();
			window.location.reload();
		} catch (error) {
			showError(error.message);
		}
	}

	function applySavedAddress(picker) {
		const addresses = (window.page_data && window.page_data.addresses) || [];
		const chosen = addresses.find((address) => address.name === picker.value);
		ADDRESS_FIELDS.forEach((field) => {
			const input = document.querySelector(`[data-shop="checkout-form"] [name="${field}"]`);
			// a new address keeps the country the shopper is in
			if (!input || (!chosen && field === "country")) return;
			input.value = (chosen && chosen[field]) || "";
		});
	}

	function syncPaymentUI() {
		const chosen = document.querySelector('input[name="payment_method"]:checked');
		const submit = document.querySelector('[data-shop="checkout-form"] [type="submit"]');
		const online = chosen && (chosen.value === "gateway" || chosen.value.startsWith("gateway:"));
		if (submit && chosen) {
			// the theme's own button wording, when it sets one
			submit.dataset.label = submit.dataset.label || submit.textContent;
			const label = online ? submit.dataset.payLabel || __("Continue to payment") : submit.dataset.label;
			submit.textContent = label;
		}
		const note = document.querySelector('[data-shop="gateway-note"]');
		if (note) note.hidden = !online;
	}

	function preselectPayment() {
		const radios = document.querySelectorAll(
			'[data-shop="checkout-form"] input[name="payment_method"]'
		);
		if (radios.length && ![...radios].some((radio) => radio.checked)) radios[0].checked = true;
	}

	async function submitReturn(form) {
		const data = new FormData(form);
		const submit = form.querySelector('[type="submit"]');
		if (submit) submit.disabled = true;
		try {
			await call("shop.storefront.returns.create_request", {
				order: window.location.pathname.split("/").filter(Boolean).pop(),
				token: new URLSearchParams(window.location.search).get("token") || undefined,
				item_code: data.get("item_code"),
				request_type: data.get("request_type"),
				qty: data.get("qty") || 1,
				reason: data.get("reason"),
			});
			window.location.reload();
		} catch (error) {
			showError(error.message, form);
			if (submit) submit.disabled = false;
		}
	}

	function initFilters() {
		const toggle = document.querySelector('[data-shop="filter-toggle"]');
		const panel = document.querySelector('[data-shop="filter-panel"]');
		if (!toggle || !panel) return;
		// applying a filter reloads the page, so the panel folds away on its own
		const close = panel.querySelector('[data-shop="filter-close"]');
		const setOpen = (open) => {
			panel.dataset.open = open ? "true" : "false";
			toggle.setAttribute("aria-expanded", open ? "true" : "false");
			// on a phone the panel covers the page: the page behind it doesn't scroll
			document.documentElement.style.overflow = open && getComputedStyle(panel).position === "fixed" ? "hidden" : "";
			if (open && close) close.focus();
		};
		toggle.addEventListener("click", () => setOpen(panel.dataset.open !== "true"));
		const shut = () => {
			setOpen(false);
			toggle.focus();
		};
		if (close) close.addEventListener("click", shut);
		document.addEventListener("keydown", (event) => {
			if (event.key === "Escape" && panel.dataset.open === "true") shut();
		});
	}

	// ---- the catalogue menu: the store's collections, and those inside each ----
	async function initCatalogMenu() {
		const toggle = document.querySelector('[data-shop="catalog-menu-toggle"]');
		const panel = document.querySelector('[data-shop="catalog-menu"]');
		if (!toggle || !panel) return;
		const allProducts = base + "/products";
		let tree = [];
		try {
			tree = (await call("shop.storefront.catalog.catalog_menu")) || [];
		} catch (e) {
			tree = [];
		}
		if (!tree.length) {
			toggle.addEventListener("click", () => (window.location.href = allProducts));
			return;
		}
		const all = `<a class="catalog-menu-all" href="${esc(allProducts)}">${esc(__("All products"))}</a>`;
		const link = (entry, label) => `<a href="${esc(entry.route)}">${esc(label || entry.title)}</a>`;
		const count = (entry) =>
			`<span>${esc(entry.count === 1 ? __("1 product") : __("{0} products", [entry.count]))}</span>`;
		const tile = (entry) => `
			<div class="catalog-menu-group">
				<a href="${esc(entry.route)}">${entry.image ? `<img src="${esc(entry.image)}" alt="" loading="lazy">` : ""}${esc(entry.title)}</a>
				${entry.children.map((child) => link(child)).join("")}
				${entry.children.length ? "" : count(entry)}
			</div>`;
		if (!tree.some((entry) => entry.children.length)) {
			// nothing inside the top collections: they are tiles
			panel.innerHTML = `<div class="catalog-menu-inner catalog-menu-flat"><div class="catalog-menu-groups">${tree.map(tile).join("")}</div>${all}</div>`;
		} else {
			panel.innerHTML = `
				<div class="catalog-menu-inner">
					<ul class="catalog-menu-list">
						${tree
							.map((entry, index) =>
								entry.children.length
									? `<li><button type="button" data-index="${index}" aria-expanded="false">${esc(entry.title)}<span aria-hidden="true">&rsaquo;</span></button></li>`
									: `<li><a href="${esc(entry.route)}">${esc(entry.title)}${count(entry)}</a></li>`
							)
							.join("")}
						<li class="catalog-menu-all">${all}</li>
					</ul>
					<div class="catalog-menu-detail"></div>
				</div>`;
			const detail = panel.querySelector(".catalog-menu-detail");
			const buttons = panel.querySelectorAll("button[data-index]");
			const show = (index) => {
				const entry = tree[index];
				buttons.forEach((button) => button.setAttribute("aria-expanded", button.dataset.index === String(index)));
				detail.innerHTML = `${link(entry, __("Shop all {0}", [entry.title]))}
					<div class="catalog-menu-groups">${entry.children.map(tile).join("")}</div>`;
			};
			show(Number(buttons[0].dataset.index));
			buttons.forEach((button) => {
				button.addEventListener("mouseenter", () => show(Number(button.dataset.index)));
				// by keyboard a group is opened, then its collections are next in line
				button.addEventListener("click", (event) => {
					show(Number(button.dataset.index));
					if (event.detail === 0) {
						const first = detail.querySelector("a");
						if (first) first.focus();
					}
				});
			});
		}
		const setOpen = (open) => {
			panel.hidden = !open;
			toggle.setAttribute("aria-expanded", open ? "true" : "false");
		};
		toggle.addEventListener("click", (event) => {
			setOpen(panel.hidden);
			// opened by keyboard: the menu is next, wherever the theme put it in the page
			if (!panel.hidden && event.detail === 0) {
				const first = panel.querySelector("button, a");
				if (first) first.focus();
			}
		});
		document.addEventListener("keydown", (event) => {
			if (event.key === "Escape" && !panel.hidden) {
				setOpen(false);
				toggle.focus();
			}
		});
		document.addEventListener("click", (event) => {
			if (!panel.hidden && !panel.contains(event.target) && !toggle.contains(event.target)) setOpen(false);
		});
	}

	// a select of links: it shows the one in use, and choosing another opens it
	function initLinkSelects() {
		document.querySelectorAll('[data-shop="link-select"]').forEach((select) => {
			const current = select.querySelector('option[data-active="true"]');
			if (current) select.value = current.value;
			select.addEventListener("change", () => {
				if (select.value) window.location.href = select.value;
			});
		});
	}

	function initBuyBar() {
		const bar = document.querySelector(".pdp-buybar");
		const anchor = document.querySelector('[data-shop="add-to-cart"]');
		if (!bar || !anchor || !("IntersectionObserver" in window)) return;
		new IntersectionObserver(
			(entries) => {
				bar.dataset.visible = entries[0].isIntersecting ? "false" : "true";
			},
			{ rootMargin: "-60px 0px 0px 0px" }
		).observe(anchor);
	}

	function initCurrencyPicker() {
		// the shopper picks the currency prices are shown in; the page is redrawn with it
		document.querySelectorAll('[data-shop="currency-picker"]').forEach((select) =>
			select.addEventListener("change", async () => {
				select.disabled = true;
				try {
					await call("shop.storefront.pricing.set_currency", { currency: select.value });
					window.location.reload();
				} catch (error) {
					select.disabled = false;
					showError(error.message);
				}
			})
		);
	}

	function initBuyingFor() {
		// a login linked to several customers picks which one it buys for; prices and terms follow
		document.addEventListener("change", async (event) => {
			const select = event.target.closest('select[data-shop="buying-for"]');
			if (!select) return;
			select.disabled = true;
			try {
				await call("shop.storefront.pricing.set_buying_for", { customer: select.value });
				window.location.reload();
			} catch (error) {
				select.disabled = false;
				showError(error.message);
			}
		});
	}

	// A select's list in the theme's style on a desktop; phones and tablets keep their own picker. The
	// select stays what forms and the store's scripts use: choosing sets it and fires its change event.
	function initSelectLists() {
		const desktop = window.matchMedia("(hover: hover) and (pointer: fine)");
		let open = null;

		const usable = (select) =>
			select instanceof HTMLSelectElement &&
			desktop.matches &&
			!select.multiple &&
			select.size <= 1 &&
			!select.disabled &&
			!select.closest("[data-native-select]");

		function close(refocus) {
			if (!open) return;
			const { select, list } = open;
			list.remove();
			select.setAttribute("aria-expanded", "false");
			select.removeAttribute("aria-controls");
			open = null;
			if (refocus) select.focus();
		}

		function choose(select, value) {
			if (select.value !== value) {
				select.value = value;
				select.dispatchEvent(new Event("input", { bubbles: true }));
				select.dispatchEvent(new Event("change", { bubbles: true }));
			}
			close(true);
		}

		function place(select, list) {
			const box = select.getBoundingClientRect();
			list.style.minWidth = `${Math.max(box.width, 160)}px`;
			const height = list.offsetHeight;
			const below = window.innerHeight - box.bottom;
			const top = below < height + 8 && box.top > below ? box.top - height - 4 : box.bottom + 4;
			list.style.top = `${top + window.scrollY}px`;
			const left = Math.min(box.left, window.innerWidth - list.offsetWidth - 8);
			list.style.left = `${Math.max(8, left) + window.scrollX}px`;
		}

		function show(select) {
			close(false);
			const style = getComputedStyle(select);
			const list = document.createElement("div");
			list.className = "shop-select-list";
			list.style.fontFamily = style.fontFamily;
			list.style.letterSpacing = style.letterSpacing;
			list.style.textTransform = style.textTransform;
			const id = `shop-select-list-${Date.now()}`;
			const options = [...select.options].filter((option) => !option.hidden);
			const searchable = options.length > 10;
			list.innerHTML = `
				${searchable ? `<input type="text" class="shop-select-search" autocomplete="off" placeholder="${esc(__("Search"))}" aria-label="${esc(__("Search"))}" aria-controls="${id}">` : ""}
				<div role="listbox" id="${id}" tabindex="-1" aria-label="${esc(select.getAttribute("aria-label") || (select.labels && select.labels[0] ? select.labels[0].textContent.trim() : "") || select.name || "")}">
					${options
						.map(
							(option, index) =>
								`<div role="option" id="${id}-${index}" data-value="${esc(option.value)}" aria-selected="${option.selected}"${option.disabled ? ' aria-disabled="true"' : ""}>${esc(option.textContent.trim())}</div>`
						)
						.join("")}
				</div>
				<p class="shop-select-empty" hidden>${esc(__("Nothing matches"))}</p>`;
			document.body.appendChild(list);
			const listbox = list.querySelector('[role="listbox"]');
			const search = list.querySelector(".shop-select-search");
			const rows = [...list.querySelectorAll('[role="option"]')];
			const visible = () => rows.filter((row) => !row.hidden && row.getAttribute("aria-disabled") !== "true");
			const focusTarget = search || listbox;
			let active = rows.find((row) => row.getAttribute("aria-selected") === "true") || visible()[0];
			const activate = (row) => {
				rows.forEach((item) => item.removeAttribute("data-active"));
				active = row;
				if (!row) return focusTarget.removeAttribute("aria-activedescendant");
				row.dataset.active = "true";
				focusTarget.setAttribute("aria-activedescendant", row.id);
				row.scrollIntoView({ block: "nearest" });
			};
			list.addEventListener("mousedown", (event) => {
				if (event.target !== search) event.preventDefault();
			});
			list.addEventListener("mousemove", (event) => {
				const row = event.target.closest('[role="option"]');
				if (row && row !== active && row.getAttribute("aria-disabled") !== "true") activate(row);
			});
			list.addEventListener("click", (event) => {
				const row = event.target.closest('[role="option"]');
				if (row && row.getAttribute("aria-disabled") !== "true") choose(select, row.dataset.value);
			});
			let typed = "";
			let typedAt = 0;
			list.addEventListener("keydown", (event) => {
				const shown = visible();
				const at = shown.indexOf(active);
				if (event.key === "ArrowDown" || event.key === "ArrowUp") {
					event.preventDefault();
					const step = event.key === "ArrowDown" ? 1 : -1;
					activate(shown[Math.min(Math.max(at + step, 0), shown.length - 1)] || shown[0]);
				} else if (event.key === "Home" || event.key === "End") {
					if (event.target === search) return;
					event.preventDefault();
					activate(event.key === "Home" ? shown[0] : shown[shown.length - 1]);
				} else if (event.key === "Enter") {
					event.preventDefault();
					if (active && !active.hidden) choose(select, active.dataset.value);
				} else if (event.key === "Escape") {
					event.preventDefault();
					close(true);
				} else if (event.key === "Tab") {
					close(true);
				} else if (!search && event.key.length === 1) {
					typed = Date.now() - typedAt > 700 ? event.key : typed + event.key;
					typedAt = Date.now();
					const match = shown.find((row) => row.textContent.trim().toLowerCase().startsWith(typed.toLowerCase()));
					if (match) activate(match);
				}
			});
			if (search)
				search.addEventListener("input", () => {
					const words = search.value.trim().toLowerCase();
					rows.forEach((row) => (row.hidden = !!words && !row.textContent.toLowerCase().includes(words)));
					list.querySelector(".shop-select-empty").hidden = visible().length > 0;
					activate(visible()[0]);
				});
			select.setAttribute("aria-expanded", "true");
			select.setAttribute("aria-controls", id);
			open = { select, list };
			place(select, list);
			activate(active);
			focusTarget.focus({ preventScroll: true });
		}

		document.addEventListener(
			"mousedown",
			(event) => {
				const select = event.target.closest && event.target.closest("select");
				if (open && !open.list.contains(event.target) && open.select !== select) close(false);
				if (!usable(select) || event.button !== 0) return;
				event.preventDefault();
				select.focus({ preventScroll: true });
				if (open && open.select === select) close(false);
				else show(select);
			},
			true
		);
		document.addEventListener("keydown", (event) => {
			const select = event.target;
			if (!usable(select) || open) return;
			const opens = [" ", "Enter", "ArrowDown", "ArrowUp", "F4"].includes(event.key);
			if (!opens) return;
			event.preventDefault();
			show(select);
		});
		window.addEventListener("resize", () => close(false));
		document.addEventListener(
			"scroll",
			(event) => {
				if (open && !open.list.contains(event.target)) place(open.select, open.list);
			},
			true
		);
	}

	// Addresses suggested as one is typed, when the store has a lookup service (Shop Settings). Any
	// form with an address_line1 input gets them; picking one fills the form's address fields.
	function initAddressLookup() {
		let enabled = true;
		let current = null;
		const token = () =>
			window.crypto && window.crypto.randomUUID ? window.crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`;

		function fieldsOf(input) {
			const scope = input.form || input.closest('[data-shop="checkout-form"]') || input.parentElement;
			const field = (name) => scope.querySelector(`[name="${name}"]`);
			return { scope, field };
		}

		function close() {
			if (!current) return;
			current.list.remove();
			current.input.setAttribute("aria-expanded", "false");
			current.input.removeAttribute("aria-activedescendant");
			current = null;
		}

		function setField(element, value) {
			if (!element || value == null) return;
			if (element instanceof HTMLSelectElement && ![...element.options].some((option) => option.value === value)) return;
			if (element.value === value) return;
			element.value = value;
			element.dispatchEvent(new Event("input", { bubbles: true }));
			element.dispatchEvent(new Event("change", { bubbles: true }));
		}

		async function pick(state, suggestion) {
			close();
			clearTimeout(state.timer);
			state.seq++;
			let address = suggestion.address;
			if (!address) {
				try {
					address = await call("shop.storefront.address_lookup.address", { id: suggestion.id, session: state.session });
				} catch (e) {
					return;
				}
			}
			state.session = token();
			const { field } = fieldsOf(state.input);
			const line2 = field("address_line2");
			setField(field("country"), address.country);
			state.picking = true;
			setField(state.input, line2 || !address.address_line2 ? address.address_line1 : `${address.address_line1}, ${address.address_line2}`);
			state.picking = false;
			setField(line2, address.address_line2);
			setField(field("city"), address.city);
			setField(field("state"), address.state);
			setField(field("pincode"), address.pincode);
			state.input.focus();
		}

		function show(state, result) {
			close();
			const suggestions = result.suggestions || [];
			if (!suggestions.length || document.activeElement !== state.input) return;
			const id = `shop-address-list-${Date.now()}`;
			const list = document.createElement("div");
			list.className = "shop-select-list shop-address-list";
			list.innerHTML = `
				<div role="listbox" id="${id}" aria-label="${esc(__("Suggested addresses"))}">
					${suggestions
						.map(
							(row, index) =>
								`<div role="option" id="${id}-${index}" data-index="${index}" aria-selected="false"><span>${esc(row.label)}</span>${row.detail ? `<small>${esc(row.detail)}</small>` : ""}</div>`
						)
						.join("")}
				</div>
				${result.attribution ? `<p class="shop-address-credit">${esc(result.attribution)}</p>` : ""}`;
			document.body.appendChild(list);
			const box = state.input.getBoundingClientRect();
			list.style.width = `${Math.max(box.width, 260)}px`;
			list.style.top = `${box.bottom + 4 + window.scrollY}px`;
			list.style.left = `${Math.max(8, Math.min(box.left, window.innerWidth - list.offsetWidth - 8)) + window.scrollX}px`;
			list.addEventListener("mousedown", (event) => event.preventDefault());
			list.addEventListener("click", (event) => {
				const row = event.target.closest('[role="option"]');
				if (row) pick(state, suggestions[Number(row.dataset.index)]);
			});
			state.input.setAttribute("aria-expanded", "true");
			state.input.setAttribute("aria-controls", id);
			current = { input: state.input, list, suggestions, active: -1, state };
		}

		function activate(index) {
			const rows = [...current.list.querySelectorAll('[role="option"]')];
			current.active = (index + rows.length) % rows.length;
			rows.forEach((row, at) => {
				row.dataset.active = at === current.active ? "true" : "false";
				row.setAttribute("aria-selected", at === current.active ? "true" : "false");
			});
			current.input.setAttribute("aria-activedescendant", rows[current.active].id);
			rows[current.active].scrollIntoView({ block: "nearest" });
		}

		const states = new WeakMap();
		function stateOf(input) {
			if (!states.has(input)) {
				input.setAttribute("role", "combobox");
				input.setAttribute("aria-autocomplete", "list");
				input.setAttribute("aria-expanded", "false");
				states.set(input, { input, session: token(), timer: null, seq: 0, picking: false });
			}
			return states.get(input);
		}

		document.addEventListener("input", (event) => {
			const input = event.target;
			if (!enabled || !(input instanceof HTMLInputElement) || input.name !== "address_line1") return;
			const state = stateOf(input);
			if (state.picking) return;
			clearTimeout(state.timer);
			const text = input.value.trim();
			if (text.length < 3) {
				state.seq++;
				return close();
			}
			state.timer = setTimeout(async () => {
				const seq = ++state.seq;
				const country = fieldsOf(input).field("country");
				let result;
				try {
					result = await call("shop.storefront.address_lookup.suggest", {
						text,
						country: country ? country.value : null,
						session: state.session,
					});
				} catch (e) {
					return;
				}
				if (!result.enabled) {
					enabled = false;
					return close();
				}
				if (seq === state.seq) show(state, result);
			}, 250);
		});
		document.addEventListener("keydown", (event) => {
			if (!current || event.target !== current.input) return;
			if (event.key === "ArrowDown" || event.key === "ArrowUp") {
				event.preventDefault();
				activate(current.active + (event.key === "ArrowDown" ? 1 : -1));
			} else if (event.key === "Enter") {
				// Enter picks an address rather than sending the form
				event.preventDefault();
				pick(current.state, current.suggestions[Math.max(current.active, 0)]);
			} else if (event.key === "Escape") {
				close();
			}
		});
		document.addEventListener("focusout", (event) => {
			if (current && event.target === current.input) close();
		});
		// a phone's toolbar hiding as the page scrolls resizes the window; only a new width moves the list
		let width = window.innerWidth;
		window.addEventListener("resize", () => {
			if (window.innerWidth !== width) close();
			width = window.innerWidth;
		});
	}

	// products listed under a search box as the shopper types; Enter on none searches as before
	function initSearchSuggestions() {
		let current = null;
		const close = () => {
			if (!current) return;
			current.list.remove();
			current.input.setAttribute("aria-expanded", "false");
			current.input.removeAttribute("aria-activedescendant");
			current = null;
		};
		const activate = (index) => {
			const rows = [...current.list.querySelectorAll('[role="option"]')];
			current.active = (index + rows.length) % rows.length;
			rows.forEach((row, at) => (row.dataset.active = at === current.active ? "true" : "false"));
			current.input.setAttribute("aria-activedescendant", rows[current.active].id);
		};
		const show = (input, result) => {
			close();
			if (!result.products.length || document.activeElement !== input) return;
			const id = `shop-search-list-${Date.now()}`;
			const all = `${base}/products?search=${encodeURIComponent(input.value.trim())}`;
			const list = document.createElement("div");
			list.className = "shop-select-list shop-search-list";
			list.innerHTML = `
				<div role="listbox" id="${id}" aria-label="${esc(__("Suggested products"))}">
					${result.products
						.map(
							(row, index) =>
								`<a role="option" id="${id}-${index}" href="${esc(row.route)}"><img src="${esc(row.image)}" alt="" loading="lazy"><span>${esc(row.title)}</span>${row.price ? `<small>${esc(row.price)}</small>` : ""}</a>`
						)
						.join("")}
					<a role="option" id="${id}-all" class="shop-search-all" href="${esc(all)}">${esc(
						result.total === 1 ? __("See the result") : __("See all {0} results", [result.total])
					)}</a>
				</div>`;
			document.body.appendChild(list);
			const box = input.getBoundingClientRect();
			list.style.width = `${Math.max(box.width, 300)}px`;
			list.style.top = `${box.bottom + 4 + window.scrollY}px`;
			list.style.left = `${Math.max(8, Math.min(box.left, window.innerWidth - list.offsetWidth - 8)) + window.scrollX}px`;
			list.addEventListener("mousedown", (event) => event.preventDefault());
			input.setAttribute("aria-expanded", "true");
			input.setAttribute("aria-controls", id);
			current = { input, list, active: -1 };
		};
		document.querySelectorAll('[data-shop="search-form"] input[name="search"]').forEach((input) => {
			input.setAttribute("role", "combobox");
			input.setAttribute("aria-autocomplete", "list");
			input.setAttribute("aria-expanded", "false");
			let timer = null;
			let seq = 0;
			input.addEventListener("input", () => {
				clearTimeout(timer);
				const text = input.value.trim();
				const mine = ++seq;
				if (text.length < 2) return close();
				timer = setTimeout(async () => {
					try {
						const result = await call("shop.storefront.catalog.search_suggestions", { text });
						if (mine === seq) show(input, result);
					} catch (e) {
						close();
					}
				}, 200);
			});
			input.addEventListener("keydown", (event) => {
				if (!current || current.input !== input) return;
				if (event.key === "ArrowDown" || event.key === "ArrowUp") {
					event.preventDefault();
					activate(current.active + (event.key === "ArrowDown" ? 1 : -1));
				} else if (event.key === "Enter" && current.active >= 0) {
					event.preventDefault();
					window.location.href = current.list.querySelectorAll('[role="option"]')[current.active].href;
				} else if (event.key === "Escape") {
					close();
				}
			});
			input.addEventListener("blur", close);
		});
	}

	// the email typed at checkout is kept with the cart, for a reminder if it's left (Shop Settings)
	function initCartEmail() {
		const input = document.querySelector('[data-shop="checkout-form"] input[name="email"]');
		if (!input) return;
		let sent = "";
		input.addEventListener("change", () => {
			const email = input.value.trim();
			if (email === sent || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return;
			sent = email;
			call("shop.storefront.cart.remember_email", { email }).catch(() => {});
		});
	}

	function init() {
		initCurrencyPicker();
		initBuyingFor();
		initGallery();
		initVariantPicker();
		refreshCartCount();
		initReviewForm();
		preselectPayment();
		syncPaymentUI();
		initBuyBar();
		initFilters();
		initLinkSelects();
		initCatalogMenu();
		initSelectLists();
		initAddressLookup();
		initCartEmail();
		initStockAlert();
		initSearchSuggestions();
		document
			.querySelectorAll('[data-shop="checkout-form"] input[name="payment_method"]')
			.forEach((radio) => radio.addEventListener("change", syncPaymentUI));
		const picker = document.querySelector('[data-shop="address-picker"]');
		if (picker)
			picker.addEventListener("change", () => {
				applySavedAddress(picker);
				scheduleQuote(0);
			});
		initCheckout();
		window.shop_storefront_ready = true;
	}

	// the script may run after the page has loaded (deferred, or added after load)
	if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
	else init();
})();
