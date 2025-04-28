import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, StoppingCriteria, StoppingCriteriaList
from transformers import T5ForConditionalGeneration


# Adopted from https://github.com/huggingface/transformers/pull/14897
class EndOfFunctionCriteria(StoppingCriteria):
    def __init__(self, start_length, eof_strings, tokenizer):
        self.start_length = start_length
        self.eof_strings = eof_strings
        self.tokenizer = tokenizer
        self.end_length = {}

    def __call__(self, input_ids, scores, **kwargs):
        """Returns true if all generated sequences contain any of the end-of-function strings."""
        decoded_generations = self.tokenizer.batch_decode(input_ids[:, self.start_length:])
        done = []
        for index, decoded_generation in enumerate(decoded_generations):
            finished = any([stop_string in decoded_generation for stop_string in self.eof_strings])
            if finished and index not in self.end_length:  # ensures first time we see it
                for stop_string in self.eof_strings:
                    if stop_string in decoded_generation:
                        self.end_length[index] = len(input_ids[index, # get length of actual generation
                                                     self.start_length:
                                                     -len(self.tokenizer.encode(stop_string, add_special_tokens=False,
                                                                                return_tensors='pt')[0])])
            done.append(finished)
        return all(done)


global_eof_stops = ['// Buggy Function', '// Fixed Function', '# Buggy Function', '# Fixed Function',
                    '/* Buggy Function */', '/* Fixed Function */', '<|endoftext|>']


class LMs(object):
    def __init__(self, batch_size: int = 1, pretrained: str = 'gpt2', stop="", weight=None):
        print("Initializing a language model: {} ...".format(pretrained))
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        # GPT-NeoX issue: https://github.com/huggingface/transformers/issues/17452
        # self.model = AutoModelForCausalLM.from_pretrained(pretrained, torch_dtype=torch.float16)
        if weight == 'float16':
            print("Switching to float16 ...")
            self.model = AutoModelForCausalLM.from_pretrained(pretrained, torch_dtype=torch.float16, trust_remote_code=True)
            self.model.to(self.device)
        elif weight == 'bfloat16':
            print("Switching to bfloat16 ...")
            self.model = AutoModelForCausalLM.from_pretrained(pretrained, torch_dtype=torch.bfloat16, trust_remote_code=True)
            self.model.to(self.device)
        elif weight == 'float32':
            print("Switching to float32 ...")
            self.model = AutoModelForCausalLM.from_pretrained(pretrained, torch_dtype=torch.float32, trust_remote_code=True)
            self.model.to(self.device)
        elif weight == 'int8':
            self.model = AutoModelForCausalLM.from_pretrained(pretrained, load_in_8bit=True, device_map="auto", trust_remote_code=True)
        elif weight == 'int4':
            print("Switching to int4 ...")
            self.model = AutoModelForCausalLM.from_pretrained(pretrained, load_in_4bit=True, device_map="auto", trust_remote_code=True)
        else:
            print("No weight type specified or unrecognized weight. Defaulting to float16 ...")
            self.model = AutoModelForCausalLM.from_pretrained(pretrained, torch_dtype=torch.float16, trust_remote_code=True)
            self.model.to(self.device)

        self.max_length = self.model.config.to_dict().get('max_position_embeddings', 2048)
        # use max position embeddings to determine max length
        print("Max length: {}".format(self.max_length))
        self.tokenizer = AutoTokenizer.from_pretrained(pretrained)
        self.stop = stop
        # TODO: add batch size
        self.batch_size = batch_size

    def check_input(self, prompt: str, buggy_func: str):
        # Check if prompt + fix_function=approx(buggy_func) will be longer than the max length
        input_tokens = self.tokenizer.encode(prompt + "\n" + buggy_func, return_tensors='pt')
        if len(input_tokens[0]) > self.max_length:
            return False
        return True

    def model_predict(self, prompt: str, buggy_func: str, do_sample=False, num_samples=10000):
        if not self.check_input(prompt, buggy_func):
            return False, False, None, None  # If the input is too long, return False
        input_tokens = self.tokenizer.encode(prompt, return_tensors='pt').repeat(min(self.batch_size, num_samples), 1)
        input_tokens = input_tokens.to(self.device)
        sc = StoppingCriteriaList([EndOfFunctionCriteria(start_length=len(input_tokens[0]),
                                                         eof_strings=[self.stop] + global_eof_stops,
                                                         tokenizer=self.tokenizer)])

        with torch.no_grad():
            raw_o = self.model.generate(input_tokens,
                                        max_length=min(self.max_length, len(input_tokens[0]) +
                                                       int(2*len(self.tokenizer.encode(buggy_func, return_tensors='pt')[0]))),
                                        stopping_criteria=sc,
                                        do_sample=do_sample,
                                        top_p=0.95,
                                        temperature=0.8,
                                        output_scores=True,
                                        return_dict_in_generate=True,
                                        pad_token_id=self.tokenizer.eos_token_id)  # remove warning
            gen_sequences = raw_o.sequences[:, len(input_tokens[0]):]
            neg_logs = -torch.log(torch.stack(raw_o.scores, dim=1).softmax(-1))
            neg_logs = torch.gather(neg_logs, 2, gen_sequences[:, :, None]).squeeze(-1)
            t_outputs = self.tokenizer.batch_decode(gen_sequences, skip_special_tokens=False)
            outputs = []
            entropies = []
            for index, output in enumerate(t_outputs):
                min_index = 10000000
                for eof_string in [self.stop] + global_eof_stops:
                    if eof_string in output:
                        min_index = min(output.index(eof_string), min_index)
                        if index not in sc[0].end_length:
                            sc[0].end_length[index] = len(gen_sequences[index,
                                                          :-len(self.tokenizer.encode(eof_string,
                                                                                      add_special_tokens=False,
                                                                                      return_tensors='pt')[0])])

                if min_index != 10000000 and sc[0].end_length[index] != 0:
                    outputs.append(output[:min_index].strip())
                    entropies.append((neg_logs[index, :sc[0].end_length[index]].sum(-1).cpu().item() / sc[0].end_length[index],
                                      neg_logs[index, :sc[0].end_length[index]].sum(-1).cpu().item()))

        return True, len(outputs) > 0, outputs, entropies


global_infill_stops = ['# Provide a fix for the buggy function', '// Provide a fix for the buggy function']

