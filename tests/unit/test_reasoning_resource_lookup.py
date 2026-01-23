
import sys
from pathlib import Path
import logging

# Set encoding
sys.stdout.reconfigure(encoding='utf-8')

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core_pipeline.ontology_manager_enhanced import EnhancedOntologyManager
from core_pipeline.reasoning_engine import ReasoningEngine

def test_resource_lookup():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("ResourceLookupTest")
    
    config = {
        "ontology_path": "./knowledge/ontology",
        "data_lake_path": "./data_lake",
        "data_paths": {} 
    }
    
    logger.info("Initializing OntologyManager...")
    om = EnhancedOntologyManager(config)
    
    logger.info("Initializing ReasoningEngine...")
    re = ReasoningEngine(config)
    
    # Test Context
    context = {
        "ontology_manager": om,
        "situation_id": "THREAT001",
        "is_first_coa": True,
        "resource_availability_provided": False # 강제 조회 유도
    }
    
    logger.info("Testing _extract_resource_availability with situation_id='THREAT001'...")
    try:
        # _extract_resource_availability is protected, but we can call it for testing
        score = re._extract_resource_availability(context)
        logger.info(f"Result Score: {score}")
        
        if score == 0.5:
             logger.warning("Score is 0.5 (Default). Check if resources were found.")
        else:
             logger.info("Score is NOT default, implying resources were found or logic applied.")
             
    except Exception as e:
        logger.error(f"Error during execution: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_resource_lookup()
