(function () {
	const state = {
		product: window.page_data && window.page_data.product,
		selection: {},
	};

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
			button.textContent = button.dataset.addedLabel || "Added";
			setTimeout(() => (button.textContent = label), 1500);
		} catch (error) {
			showError(error.message);
		} finally {
			button.disabled = false;
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
		const buy = document.querySelector('[data-shop="add-to-cart"]');
		if (!variant) {
			if (buy) buy.disabled = true;
			return;
		}
		if (buy) {
			buy.dataset.itemCode = variant.item_code;
			buy.disabled = !variant.in_stock;
			if (!variant.in_stock) buy.textContent = buy.dataset.outOfStockLabel || "Out of stock";
			else if (buy.dataset.label) buy.textContent = buy.dataset.label;
		}
		const price = document.querySelector('[data-shop="pdp-price"]');
		if (price && variant.formatted_price) price.textContent = variant.formatted_price;
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
		const target = event.target.closest("[data-shop]");
		if (!target) return;
		const action = target.dataset.shop;
		if (action === "add-to-cart") addToCart(target);
		else if (action === "variant-option") selectOption(target);
		else if (action === "qty-inc") setQty(target.dataset.itemCode, rowQty(target.dataset.itemCode) + 1);
		else if (action === "qty-dec") setQty(target.dataset.itemCode, rowQty(target.dataset.itemCode) - 1);
		else if (action === "remove") setQty(target.dataset.itemCode, 0);
	});

	document.addEventListener("submit", (event) => {
		const form = event.target.closest("[data-shop]");
		if (!form) return;
		if (form.dataset.shop === "checkout-form") {
			event.preventDefault();
			submitCheckout(form);
		} else if (form.dataset.shop === "search-form") {
			event.preventDefault();
			const term = form.querySelector('[name="search"]');
			window.location.href = "/products?search=" + encodeURIComponent(term ? term.value : "");
		}
	});

	document.addEventListener("DOMContentLoaded", () => {
		initVariantPicker();
		refreshCartCount();
	});
})();
