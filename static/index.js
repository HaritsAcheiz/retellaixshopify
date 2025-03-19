document.addEventListener('DOMContentLoaded', () => {
  const AppBridge = window['app-bridge'];
  const createApp = AppBridge.default;

  async function initializeAppBridge() {
    const urlParams = new URLSearchParams(window.location.search);
    const shop = urlParams.get('shop');
    if (!shop) {
      console.error('Shop parameter is missing!');
      return;
    }

    try {
      const response = await fetch(`/api/init?shop=${shop}`);
      const data = await response.json();
      if (response.ok) {
        const app = createApp({
          apiKey: data.apiKey,
          host: btoa(`${data.shopOrigin}/admin`),
        });

        const Toast = AppBridge.actions.Toast;
        const toast = Toast.create(app, { 
          message: 'Welcome to your Shopify App!', 
          duration: 3000 
        });
        toast.dispatch(Toast.Action.SHOW);

        const TitleBar = AppBridge.actions.TitleBar;
        TitleBar.create(app, { title: 'Order Shipping Labels' });
         
        return app;
      } else {
          console.error('Failed to initialize App Bridge:', data.error);
        }
    } catch (error) {
        console.error('Error fetching API key:', error);
      }
  }

  // Initialize App Bridge
  initializeAppBridge();

  // Search functionality
  const fetchButton = document.getElementById('fetchButton');
  const searchBox = document.getElementById('searchBox');

  fetchButton.addEventListener('click', (event) => {
        event.preventDefault(); // Prevent default form submission
        const orderId = searchBox.value.trim();

        if (!orderId) {
            alert('Please enter an Order ID to search.');
            return;
        }

        clearError(); // Clear any previous error messages

        // Redirect to the search_order endpoint with the order ID
        window.location.href = `/search_order?orderid=${encodeURIComponent(orderId)}`;
    });

    // Add keypress event listener for search box
    searchBox.addEventListener('keypress', (event) => {
        
        if (event.key === 'Enter') {
            fetchButton.click();
        }
    });

    // Function to display error messages
    function displayError(message) {
        errorContainer.style.display = 'block';
        errorContainer.textContent = message;
    }

    // Function to clear error messages
    function clearError() {
        errorContainer.style.display = 'none';
        errorContainer.textContent = '';
    }
});

// Define the viewOrderDetails function outside the event listener
    function viewOrderDetails(orderName) {
      window.location.href = `/order-details?ordername=${encodeURIComponent(orderName)}`;
    }