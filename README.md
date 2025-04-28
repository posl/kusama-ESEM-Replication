# How Small is Enough? Empirical Evidence of Quantized Small Language Models for Automated Program Repair

This repository contains the code used to run the experiments.

### Setup Environment
1. Clone the repository or download the project files.
2. Install the dependencies listed in requierments.txt by running the following command:
```
pip install -r requirements.txt
```

### Patch Generation

You can find the main patch generation logic in `LLM_repair/Repair` folder

#### Local model generations
Before running the patch generation for the local model, navigate to the `LLM_repair/Repair/LM` directory:
```
cd LLM_repair/Repair/LM
```

Example usage to run repair:
```
python3 repair.py --model_name EleutherAI/gpt-neo-1.3B --batch_size 10 --dataset quixbugs-python --chances 200 --skip_val  --weight float16 --folder Results/test_generation
```
This will generate the patches and store them in the specified folder (Results/test_generation).

#### Codex model generations
place your OpenAI access key in `Repair/Codex/api_key.txt`

Then, navigate to the `LLM_repair/Repair/Codex` directory

```
python codex_repair --chances 200 --skip_val --folder Results/test_generation 
```

#### Arguments description:
- model_name: The Hugging Face model name to use for patch generation (e.g., EleutherAI/gpt-neo-1.3B).
- batch_size: Number of inputs processed at once. Affects speed and memory usage.
- dataset: Target dataset for repair (quixbugs-python, quixbugs-java).
- chances: Maximum number of patch attempts per bug.
- skip_val: If set, validation during patch generation is skipped.
- folder: Directory where the generated patches will be saved.
- weight: Quantization weight type for the model, such as float16. For RQ2, please change this option to experiment with different quantization settings.


### Patch Validation

The validation function can be found in the `LLM_Repair/Dataset` folder with the appropriate function to validate each of the repair datasets.

Before validating patches, navigate to the `LLM_repair/Dataset` directory.

Example usage for the QuixBugs-Python dataset:
```
python3 -c "from validate_quixbug import validate_all_patches; validate_all_patches('../Repair/LM/Results/test_generation', 'lm.json')"
```
If you are validating patches generated for the QuixBugs-Java dataset, use validate_quixbug_java instead.


### License and Acknowledgements

This project is based on the following works. For more details, please refer to the `LICENSE` file.
- QuixBugs dataset
  - Original Author: James Koppel
  - License: MIT License
  - URL: https://github.com/jkoppel/QuixBugs?tab=MIT-1-ov-file
- Replication package of “Automated Program Repair in the Era of Large Pre-Trained Language Models”
  - Original Author: Xia Chunqiu, Wei Yuxiang, Zhang Lingming
  - License: Creative Commons Attribution 4.0 International (CC BY 4.0)
  - URL: https://zenodo.org/records/7622931