from flask import Flask, render_template_string

app = Flask(__name__)

@app.route('/')
def index():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Tab Test</title>
    <style>
        .tab {
            cursor: pointer;
            padding: 10px;
            background-color: #f1f1f1;
            border: 1px solid #ccc;
            display: inline-block;
            margin-right: 5px;
        }
        .tab-content {
            display: none;
            padding: 20px;
            border: 1px solid #ccc;
            margin-top: 10px;
        }
        .tab.active {
            background-color: #007bff;
            color: white;
        }
        .tab-content.active {
            display: block;
        }
    </style>
</head>
<body>
    <div>
        <div class="tab active" onclick="switchTab(event, 'tab1')">Tab 1</div>
        <div class="tab" onclick="switchTab(event, 'tab2')">Tab 2</div>
        <div class="tab" onclick="switchTab(event, 'tab3')">Tab 3</div>
    </div>
    
    <div id="tab1" class="tab-content active">Tab 1 Content</div>
    <div id="tab2" class="tab-content">Tab 2 Content</div>
    <div id="tab3" class="tab-content">Tab 3 Content</div>
    
    <script>
        // Simple global function for tab switching
        function switchTab(evt, tabId) {
            console.log('Switching to tab:', tabId);
            
            // Hide all tab contents
            var tabContents = document.getElementsByClassName('tab-content');
            for (var i = 0; i < tabContents.length; i++) {
                tabContents[i].className = tabContents[i].className.replace(' active', '');
            }
            
            // Remove active class from all tabs
            var tabs = document.getElementsByClassName('tab');
            for (var i = 0; i < tabs.length; i++) {
                tabs[i].className = tabs[i].className.replace(' active', '');
            }
            
            // Show the selected tab content and mark tab as active
            document.getElementById(tabId).className += ' active';
            evt.currentTarget.className += ' active';
        }
    </script>
</body>
</html>
    """)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
