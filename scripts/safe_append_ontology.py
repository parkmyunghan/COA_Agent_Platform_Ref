
import logging
from pathlib import Path

def run_append():
    logging.basicConfig(level=logging.INFO)

    ontology_dir = Path("c:/POC/COA_Agent_Platform/knowledge/ontology")
    instances_file = ontology_dir / "instances.ttl"
    enhancement_file = ontology_dir / "ontology_enhancement.ttl"

    try:
        # 1. Read Enhancement Content (UTF-8)
        if not enhancement_file.exists():
            logging.warning(f"Enhancement file not found: {enhancement_file}")
            return
            
        with open(enhancement_file, 'r', encoding='utf-8') as f:
            enhancement_content = f.read()

        # Check if already appended
        if not instances_file.exists():
            logging.warning(f"Instances file not found: {instances_file}")
            return
            
        with open(instances_file, 'r', encoding='utf-8') as f:
            current_content = f.read()
            
        marker = "# --- Enchanced Data (Relevance & Resources) ---"
        if marker in current_content:
            logging.info("Enhanced data marker already found. Skipping append.")
        else:
            # 2. Append to Instances File (UTF-8)
            # Ensure there is a newline separator
            with open(instances_file, 'a', encoding='utf-8') as f:
                f.write("\n\n" + marker + "\n")
                f.write(enhancement_content)
            
            logging.info(f"Successfully appended {len(enhancement_content)} bytes to instances.ttl")
            
        logging.info(f"Final size of instances.ttl: {instances_file.stat().st_size}")

    except Exception as e:
        logging.error(f"Failed to append: {e}")

if __name__ == "__main__":
    run_append()
