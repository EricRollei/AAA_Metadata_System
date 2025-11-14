class WorkflowExtractorNode:
    """Node to extract workflow metadata from existing images"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_path": ("STRING", {"default": "", "multiline": False}),
            },
            "optional": {
                "debug_logging": ("BOOLEAN", {"default": False}),
            }
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("metadata_json",)
    FUNCTION = "extract_workflow"
    CATEGORY = "Eric's Nodes/Metadata"
    
    def extract_workflow(self, image_path, debug_logging=False):
        from custom_nodes.AAA_Metadata_System.eric_metadata.workflow_metadata import WorkflowMetadataProcessor
        
        # Create processor
        processor = WorkflowMetadataProcessor(debug=debug_logging)
        
        # Process embedded data
        metadata = processor.process_embedded_data(image_path)
        
        # Convert to JSON string
        metadata_json = json.dumps(metadata, indent=2)
        
        return (metadata_json,)