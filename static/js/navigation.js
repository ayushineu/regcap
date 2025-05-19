// Simple navigation functionality for RegCap GPT
document.addEventListener('DOMContentLoaded', function() {
    // Find all navigation items in the sidebar
    const navItems = document.querySelectorAll('.nav-item');
    
    // Add click handlers to each navigation item
    navItems.forEach(function(item) {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Skip if this is the features toggle
            if (this.id === 'featureToggle') {
                return;
            }
            
            // Get the panel ID from data attribute
            const panelId = this.getAttribute('data-panel');
            if (!panelId) return;
            
            console.log('Navigation item clicked:', panelId);
            
            // Handle navigation change
            switchToPanel(panelId, this);
        });
    });
    
    // Panel switching function
    function switchToPanel(panelId, clickedItem) {
        // Hide all content panels
        const panels = document.querySelectorAll('.content-panel');
        panels.forEach(panel => panel.classList.remove('active'));
        
        // Show the selected panel
        const targetPanel = document.getElementById(panelId);
        if (targetPanel) {
            targetPanel.classList.add('active');
        }
        
        // Update active navigation item
        navItems.forEach(item => item.classList.remove('active'));
        if (clickedItem) {
            clickedItem.classList.add('active');
        }
        
        // Update the panel title
        const titles = {
            'chat-panel': '<i class="fa fa-comments"></i> Chat with your Documents',
            'docs-panel': '<i class="fa fa-file-pdf-o"></i> Document Management',
            'diagrams-panel': '<i class="fa fa-sitemap"></i> Generated Diagrams',
            'sessions-panel': '<i class="fa fa-database"></i> Session Management',
            'about-panel': '<i class="fa fa-info-circle"></i> About Us'
        };
        
        const titleElement = document.getElementById('currentPanelTitle');
        if (titleElement && titles[panelId]) {
            titleElement.innerHTML = titles[panelId];
        }
        
        // On mobile, close the sidebar
        if (window.innerWidth <= 768) {
            const sidebar = document.getElementById('sidebar');
            const overlay = document.getElementById('menuOverlay');
            if (sidebar) sidebar.classList.remove('mobile-active');
            if (overlay) overlay.classList.remove('active');
            document.body.style.overflow = '';
        }
    }
});