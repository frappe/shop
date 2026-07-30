(function () {
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

	async function call(method, args) {
		const response = await fetch(`/api/method/${method}`, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				"X-Frappe-CSRF-Token": (window.frappe && window.frappe.csrf_token) || "",
			},
			body: JSON.stringify(args || {}),
		});
		const body = await response.json();
		if (!response.ok) throw new Error(serverMessage(body));
		return body.message;
	}

	function serverMessage(body) {
		try {
			const messages = JSON.parse(body._server_messages || "[]");
			if (messages.length) return JSON.parse(messages[0]).message.replace(/<[^>]+>/g, "");
		} catch (e) {}
		return "Something went wrong. Please try again.";
	}

	function showError(message) {
		const target = document.querySelector('[data-shop="error"]');
		if (target) {
			target.textContent = message;
			target.style.display = "block";
		} else {
			alert(message);
		}
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

	async function addToCart(button) {
		const itemCode = button.dataset.itemCode;
		if (!itemCode) return;
		button.disabled = true;
		const label = button.textContent;
		try {
			const cart = await call("shop.storefront.cart.add_item", { item_code: itemCode });
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
		const cart = await call("shop.storefront.cart.get_cart");
		renderDrawer(cart);
		openDrawer();
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
					<a class="drawer-name" href="/product/${esc(item.slug || "")}">${esc(item.product_name || item.item_code)}</a>
					<span class="drawer-rate">${esc(item.formatted_rate || "")}</span>
					<div class="drawer-qty">
						<button type="button" data-drawer-step="-1" data-item-code="${esc(item.item_code)}" aria-label="Decrease quantity">&minus;</button>
						<span>${esc(item.qty)}</span>
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
		const qty = step === 0 ? 0 : Math.max((row ? row.qty : 1) + step, 0);
		try {
			const cart = await call("shop.storefront.cart.set_qty", { item_code: itemCode, qty: qty });
			renderDrawer(cart);
		} catch (error) {
			showError(error.message);
		}
	}

	async function setQty(itemCode, qty) {
		try {
			await call("shop.storefront.cart.set_qty", { item_code: itemCode, qty: qty });
			window.location.reload();
		} catch (error) {
			showError(error.message);
		}
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

	function initVariantPicker() {
		const product = state.product;
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

	function syncVariantUI() {
		document.querySelectorAll('[data-shop="variant-option"]').forEach((button) => {
			const selected = state.selection[button.dataset.attribute] === button.dataset.value;
			button.dataset.selected = selected ? "true" : "false";
			button.setAttribute("aria-pressed", selected ? "true" : "false");
		});
		const variant = selectedVariant();
		const buttons = document.querySelectorAll('[data-shop="add-to-cart"], [data-shop="buy-now"]');
		if (!variant) {
			buttons.forEach((button) => (button.disabled = true));
			return;
		}
		buttons.forEach((button) => {
			button.dataset.itemCode = variant.item_code;
			button.disabled = !variant.in_stock;
			if (!variant.in_stock)
				button.textContent = button.dataset.outOfStockLabel || "Out of stock";
			else if (button.dataset.label) button.textContent = button.dataset.label;
		});
		const price = document.querySelector('[data-shop="pdp-price"]');
		if (price && variant.formatted_price) price.textContent = variant.formatted_price;
		if (variant.image) showImage(variant.image);
	}

	async function buyNow(button) {
		const itemCode = button.dataset.itemCode;
		if (!itemCode) return;
		button.disabled = true;
		try {
			await call("shop.storefront.cart.add_item", { item_code: itemCode });
			window.location.href = "/checkout";
		} catch (error) {
			showError(error.message);
			button.disabled = false;
		}
	}

	async function submitCheckout(form) {
		const data = new FormData(form);
		const submit = form.querySelector('[type="submit"]');
		if (submit) submit.disabled = true;
		try {
			const result = await call("shop.storefront.checkout.place_order", {
				customer: {
					email: data.get("email"),
					full_name: data.get("full_name"),
					phone: data.get("phone"),
				},
				address: {
					address_line1: data.get("address_line1"),
					address_line2: data.get("address_line2"),
					city: data.get("city"),
					state: data.get("state"),
					country: data.get("country"),
					pincode: data.get("pincode"),
				},
				payment_method: data.get("payment_method") || "cod",
			});
			window.location.href = result.payment_url || result.confirmation_url;
		} catch (error) {
			showError(error.message);
			if (submit) submit.disabled = false;
		}
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
		else if (action === "add-to-cart") addToCart(target);
		else if (action === "buy-now") buyNow(target);
		else if (action === "thumb") showImage(target.dataset.image);
		else if (action === "rating-star") selectRating(parseInt(target.dataset.value, 10));
		else if (action === "variant-option") selectOption(target);
		else if (action === "qty-inc") setQty(target.dataset.itemCode, rowQty(target.dataset.itemCode) + 1);
		else if (action === "qty-dec") setQty(target.dataset.itemCode, rowQty(target.dataset.itemCode) - 1);
		else if (action === "remove") setQty(target.dataset.itemCode, 0);
	});

	document.addEventListener("keydown", (event) => {
		if (event.key === "Escape") closeDrawer();
	});

	document.addEventListener("submit", (event) => {
		const form = event.target.closest("[data-shop]");
		if (!form) return;
		if (form.dataset.shop === "checkout-form") {
			event.preventDefault();
			submitCheckout(form);
		} else if (form.dataset.shop === "review-form") {
			event.preventDefault();
			submitReview(form);
		} else if (form.dataset.shop === "coupon-form") {
			event.preventDefault();
			applyCoupon(form);
		} else if (form.dataset.shop === "search-form") {
			event.preventDefault();
			const term = form.querySelector('[name="search"]');
			window.location.href = "/products?search=" + encodeURIComponent(term ? term.value : "");
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
				"/login?redirect-to=" + encodeURIComponent(window.location.pathname)
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
			showError("Pick a star rating first.");
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
			window.location.reload();
		} catch (error) {
			showError(error.message);
			if (submit) submit.disabled = false;
		}
	}

	async function applyCoupon(form) {
		const input = form.querySelector('[name="code"]');
		if (!input || !input.value.trim()) return;
		const submit = form.querySelector('[type="submit"]');
		if (submit) submit.disabled = true;
		try {
			await call("shop.storefront.cart.apply_coupon", { code: input.value.trim() });
			window.location.reload();
		} catch (error) {
			showError(error.message);
			if (submit) submit.disabled = false;
		}
	}

	async function removeCoupon() {
		try {
			await call("shop.storefront.cart.remove_coupon", {});
			window.location.reload();
		} catch (error) {
			showError(error.message);
		}
	}

	function preselectPayment() {
		const radios = document.querySelectorAll(
			'[data-shop="checkout-form"] input[name="payment_method"]'
		);
		if (radios.length && ![...radios].some((radio) => radio.checked)) radios[0].checked = true;
	}

	document.addEventListener("DOMContentLoaded", () => {
		initGallery();
		initVariantPicker();
		refreshCartCount();
		initReviewForm();
		preselectPayment();
	});
})();
