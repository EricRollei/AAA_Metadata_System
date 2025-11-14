import { app } from "../scripts/app.js";

console.log("LoRA Gallery Extension: Loading from ComfyUI extensions directory...");

// Register the extension
app.registerExtension({
    name: "MetadataSystem.LoRAGallery",
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "LoRAGalleryWithEdit_v03") {
            console.log("LoRA Gallery Extension: Found LoRAGalleryWithEdit_v03 node");
            
            const onExecuted = nodeType.prototype.onExecuted;
            
            nodeType.prototype.onExecuted = function(message) {
                console.log("LoRA Gallery Extension: Node executed");
                console.log("Message received:", message);
                
                const result = onExecuted?.apply(this, arguments);
                
                // Check for gallery HTML in the message
                if (message && message.ui && message.ui.gallery_html && message.ui.gallery_html[0]) {
                    console.log("LoRA Gallery Extension: Found gallery HTML, length:", message.ui.gallery_html[0].length);
                    this.showGalleryPopup(message.ui.gallery_html[0], message.ui.lora_data, message.ui.edit_mode);
                } else {
                    console.log("LoRA Gallery Extension: No gallery HTML found in message.ui");
                    if (message && message.ui) {
                        console.log("Available message.ui keys:", Object.keys(message.ui));
                    } else if (message) {
                        console.log("Available message keys:", Object.keys(message));
                    }
                }
                
                return result;
            };
            
            // Add the popup functionality to the node prototype
            nodeType.prototype.showGalleryPopup = function(htmlContent, loraDataArray, editModeArray) {
                console.log("LoRA Gallery Extension: Creating popup...");
                
                // Remove existing popup
                const existing = document.getElementById('lora-gallery-popup');
                if (existing) {
                    existing.remove();
                    console.log("LoRA Gallery Extension: Removed existing popup");
                }
                
                // Create popup container
                const popup = document.createElement('div');
                popup.id = 'lora-gallery-popup';
                popup.style.cssText = `
                    position: fixed;
                    top: 50px;
                    right: 20px;
                    width: 70vw;
                    max-width: 1200px;
                    height: 80vh;
                    background: #1a1a1a;
                    border: 2px solid #4a9eff;
                    border-radius: 8px;
                    z-index: 10000;
                    overflow: hidden;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
                    display: flex;
                    flex-direction: column;
                `;
                
                // Add header with close button
                const header = document.createElement('div');
                header.style.cssText = `
                    background: #333;
                    padding: 8px 12px;
                    border-bottom: 1px solid #555;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    color: #fff;
                    font-size: 12px;
                    flex-shrink: 0;
                `;
                
                header.innerHTML = `
                    <span>LoRA Gallery ${editModeArray && editModeArray[0] ? '(Edit Mode)' : ''}</span>
                    <button onclick="document.getElementById('lora-gallery-popup').remove()" style="
                        background: #ff4757;
                        color: white;
                        border: none;
                        border-radius: 3px;
                        padding: 4px 8px;
                        cursor: pointer;
                        font-size: 11px;
                    ">✕ Close</button>
                `;
                
                // Add content container
                const content = document.createElement('div');
                content.style.cssText = `
                    flex: 1;
                    overflow: auto;
                    background: #1a1a1a;
                `;
                
                // Insert the gallery HTML
                content.innerHTML = htmlContent || '<div style="padding: 20px; color: #fff;">No gallery content available</div>';
                
                // Assemble popup
                popup.appendChild(header);
                popup.appendChild(content);
                
                // Add to page
                document.body.appendChild(popup);
                
                console.log("LoRA Gallery Extension: Popup created and added to DOM");
                
                // Make popup draggable by header
                this.makeDraggable(popup, header);
            };
            
            // Add draggable functionality
            nodeType.prototype.makeDraggable = function(element, handle) {
                let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;
                
                handle.onmousedown = dragMouseDown;
                handle.style.cursor = 'move';
                
                function dragMouseDown(e) {
                    e = e || window.event;
                    e.preventDefault();
                    pos3 = e.clientX;
                    pos4 = e.clientY;
                    document.onmouseup = closeDragElement;
                    document.onmousemove = elementDrag;
                }
                
                function elementDrag(e) {
                    e = e || window.event;
                    e.preventDefault();
                    pos1 = pos3 - e.clientX;
                    pos2 = pos4 - e.clientY;
                    pos3 = e.clientX;
                    pos4 = e.clientY;
                    
                    const newTop = element.offsetTop - pos2;
                    const newLeft = element.offsetLeft - pos1;
                    
                    // Keep within viewport
                    const maxLeft = window.innerWidth - element.offsetWidth;
                    const maxTop = window.innerHeight - element.offsetHeight;
                    
                    element.style.top = Math.max(0, Math.min(newTop, maxTop)) + "px";
                    element.style.left = Math.max(0, Math.min(newLeft, maxLeft)) + "px";
                    element.style.right = 'auto';
                }
                
                function closeDragElement() {
                    document.onmouseup = null;
                    document.onmousemove = null;
                }
            };
        }
    }
});

console.log("LoRA Gallery Extension: Registration complete");