(function () {
    const formSelector = '#stripe-payment-form';

    function showMessage(element, text, variant) {
        if (!element) {
            return;
        }
        element.textContent = text;
        element.hidden = false;
        if (variant) {
            element.dataset.variant = variant;
        }
    }

    function setLoading(button, originalText, loading) {
        if (!button) {
            return;
        }
        button.disabled = loading;
        button.textContent = loading ? 'Processing...' : originalText;
    }

    async function fetchJson(url) {
        const response = await fetch(url, {
            headers: {
                'Accept': 'application/json'
            }
        });
        if (!response.ok) {
            const message = await response.text();
            throw new Error(message || 'Request failed');
        }
        return response.json();
    }

    document.addEventListener('DOMContentLoaded', function () {
        const form = document.querySelector(formSelector);
        if (!form) {
            return;
        }
        const intentUrl = form.dataset.intentUrl;
        const confirmUrl = form.dataset.confirmUrl;
        const messageEl = form.querySelector('[data-stripe-message]');
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn ? submitBtn.textContent : '';

        if (!intentUrl || !confirmUrl) {
            showMessage(messageEl, 'Missing Stripe configuration.', 'error');
            return;
        }

        if (typeof Stripe !== 'function') {
            showMessage(messageEl, 'Stripe.js is not available.', 'error');
            return;
        }

        let stripeInstance;
        let elements;

        (async function initialise() {
            try {
                setLoading(submitBtn, originalText, true);
                const data = await fetchJson(intentUrl);
                if (!data.client_secret || !data.publishable_key) {
                    throw new Error('Stripe intent is not ready.');
                }
                stripeInstance = Stripe(data.publishable_key);
                elements = stripeInstance.elements({ clientSecret: data.client_secret });
                const paymentElement = elements.create('payment');
                paymentElement.mount('#stripe-payment-element');
                showMessage(messageEl, 'Ready to charge the card.', 'info');
            } catch (error) {
                showMessage(messageEl, error.message || 'Unable to setup Stripe.', 'error');
                return;
            } finally {
                setLoading(submitBtn, originalText, false);
            }
        }());

        form.addEventListener('submit', async function (event) {
            event.preventDefault();
            if (!stripeInstance || !elements) {
                showMessage(messageEl, 'Stripe is not initialised yet.', 'error');
                return;
            }
            setLoading(submitBtn, originalText, true);
            showMessage(messageEl, 'Processing payment...', 'info');
            try {
                const result = await stripeInstance.confirmPayment({
                    elements: elements,
                    redirect: 'if_required'
                });
                if (result.error) {
                    throw new Error(result.error.message || 'Card confirmation failed.');
                }
                const paymentIntent = result.paymentIntent;
                if (!paymentIntent) {
                    throw new Error('Payment could not be confirmed.');
                }
                if (paymentIntent.status !== 'succeeded') {
                    showMessage(messageEl, 'Payment status: ' + paymentIntent.status, 'info');
                    setLoading(submitBtn, originalText, false);
                    return;
                }
                await fetch(confirmUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify({ payment_intent: paymentIntent.id })
                });
                showMessage(messageEl, 'Payment succeeded.', 'success');
                setTimeout(function () {
                    window.location.reload();
                }, 1000);
            } catch (error) {
                showMessage(messageEl, error.message || 'Payment failed.', 'error');
                setLoading(submitBtn, originalText, false);
            }
        });
    });
}());
