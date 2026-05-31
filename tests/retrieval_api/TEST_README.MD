## How to Run `eval.py`

Start retrieval docker service with ingested docs

Start your virtual env
open Terminal from Orca directory

```export PYTHONPATH=home/shashi/AltGAN/Orca/```

```cd tests/retrieval_api```

```pip install -r requirements.txt ```

cd back to root directory (Orca)
```cd ../```
```cd ../```

```python3 tests/retrieval_api/answers_for_eval.py```

eval files will be saved to ./data/tests/retrieval_api/ folder

## How to Run `answers_for_eval.py`

This script is designed to evaluate the performance of a retrieval system by comparing its generated answers to a set of ground truth answers.  It calculates metrics like precision, recall, and F1-score.

**Prerequisites:**

*   Running Docker service in the location provided in the code.

**Input Data:**

The script expects two input files:


**Running the Script:**

1.  **Navigate to the Orca directory** 
2. Run ```python3 tests/retrieval_api/answers_for_eval.py ```


