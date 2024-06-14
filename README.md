# polysolvermod benchmark

This repo hosts benchmark results of [polysolvermod](https://github.com/svm-zhang/polysolverMod) on data from 1000 genome project for both HLA Class I and II alleles.

`polysolvermod` achieves similar accuracy as the original `polysovler` program (not suprisingly as the former is a re-engineered version of the latter). At 4-digit resolution `polysolvermod` accurately typed about 94% and 95% alleles for
Asian and CEU samples, respectively. This is on par with the [benchmark study](https://www.nature.com/articles/jhg2016141) previously reported. The footprint of typing error at 4-digits is also similar what the paper reported, as `polysolvermod` has bettern typing accuracy for HLA A and C alleles, compared to the B allele.

`polysolvermod` extends the capability of the original `polysolver` algorithm to Class II alleles. The accuracies on both Asian and CEU samples are well above 80%. And they get further boosted to 90% when controlling for number of mismatch events per alignment.

## Understand benchmark files

* Files without `eval` in the suffix are the typing results
* Files with `eval` in the suffix are the ones used for accuracy evaluation

Columns in the evaluation result files:
* p1 and p2: predicted alleles from `polysolvermod`
* e1 and e2: expected alleles from 1000 genome HLA typing result
* n_match: number of predicted alleles matching the expected ones per HLA gene

## Runtime profiling

`polysolvermod` tries to have improved runtime over the original `polysolver`. The plot below demonstrates the runtime improvement on fishing + realignment. `polysolvermod` reduces runtime across the board (orange vs. purple bar). The runtime is profiled in minute, and it is an average across multiple runs.
![runtime](./benchmark/runtime.png)

## Useful scripts

The script folder within the repo offers some useful scripts:
1. `prep_benchmark_data.sh` is a bash script to download a specified sample from the 1000 genome AWS S3 bucket
2. `jobfy_hlatyping` can be used for making SLURM job script for `polysolvermod`
3. `evaluate_1kg.R` is the script used to generate the evaluation results

To run all these tools, you will need:
1. AWS CLI tool
2. samtools >=1.13
3. python >=3.8
4. R with data.table and splitstackshape packages

## Disclaimer

You should always take a grain of salt when looking at the results offered in this repo. I encourage you to have an independent evaluation of `polysolvermod`, as I am human and subject to make mistakes. Moreover, the accuracy profile is only based on a subset of 1000 genome populations, and I do not have the computing resource to run them all. Lastly, the accuracy shown here only provides guidance, and does not reflect the performance on real-world samples, such as the ones from a clinical trial.
