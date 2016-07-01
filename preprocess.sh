#!/bin/env bash
#
#SBATCH -p all                # partition (queue)
#SBATCH -n 10                      # number of cores
#SBATCH -t 360                 # time (minutes)
#SBATCH -o /jukebox/wang/deverett/logs/%A.%a.out        # STDOUT
#SBATCH --mem=10000      #in MB

. activate py2

xvfb-run --auto-servernum --server-num=1 python preprocessing.py $SLURM_ARRAY_TASK_ID
