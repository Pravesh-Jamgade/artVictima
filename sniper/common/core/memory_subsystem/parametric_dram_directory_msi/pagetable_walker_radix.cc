#include "pagetable_walker_radix.h"
#include "cache_cntlr.h"
#include "pwc.h"
#include "subsecond_time.h"
#include <math.h> 
#include <fstream>
#include <inttypes.h>
#include <stdlib.h>
#include <time.h>
#include <algorithm>
#include <sstream>


namespace ParametricDramDirectoryMSI{

    int PageTableWalkerRadix::counter = 0;

    void ProposedHistogram::update(UInt64 value){
        UInt64 bucket = 0;
        UInt64 shifted = value;
        while (shifted > 1 && bucket + 1 < kBuckets)
        {
            shifted >>= 1;
            bucket++;
        }
        buckets[bucket]++;
        total++;
        sum += value;
        if(total == 1){
            min = value;
            max = value;
        } else {
            min = std::min(min, value);
            max = std::max(max, value);
        }

         // tail zoom bins
        if (value >= TAIL_START && value < TAIL_END) {
            tail_bins[(value - TAIL_START) / TAIL_W]++;
        }
    }

    double ProposedHistogram::average() const{
        return total ? static_cast<double>(sum) / static_cast<double>(total) : 0.0;
    }

    void ProposedHistogram::print(FILE *fp, const char *label, int width) const{
        if(!fp)
            return;
        UInt64 max_count = 0;
        for (UInt64 count : buckets)
            max_count = std::max(max_count, count);
        fprintf(fp, "%s (total=%" PRIu64 ", min=%" PRIu64 ", max=%" PRIu64 ", avg=%.2f)\n", label, total, min, max, average());
        if(max_count == 0)
            return;
        for (int idx = 0; idx < kBuckets; ++idx){
            UInt64 count = buckets[idx];
            if(!count)
                continue;
            UInt64 range_start = (idx == 0) ? 0 : (UInt64(1) << idx);
            UInt64 range_end = (idx + 1 < kBuckets) ? ((UInt64(1) << (idx + 1)) - 1) : 0;
            int bar_len = static_cast<int>(count * width / max_count);
            fprintf(fp, "  [%8" PRIu64 "..", range_start);
            if(idx + 1 < kBuckets)
                fprintf(fp, "%8" PRIu64 "] ", range_end);
            else
                fprintf(fp, "    inf] ");
            for (int c = 0; c < bar_len; ++c)
                fputc('#', fp);
            fprintf(fp, " (%" PRIu64 ")\n", count);
        }
    }

    void ProposedHistogram::printCsv(FILE *fp, const char *metric_name) const{
        if(!fp)
            return;
        fprintf(fp, "%s_avg,%.2f\n", metric_name, average());
        std::vector<std::pair<std::string, UInt64>> entries;
        entries.reserve(kBuckets);
        for (int idx = 0; idx < kBuckets; ++idx){
            UInt64 count = buckets[idx];
            if(!count)
                continue;
            UInt64 range_start = (idx == 0) ? 0 : (UInt64(1) << idx);
            std::ostringstream label;
            label << "[" << range_start << "..";
            if(idx + 1 < kBuckets){
                UInt64 range_end = (UInt64(1) << (idx + 1)) - 1;
                label << range_end << "]";
            } else {
                label << "inf]";
            }
            entries.emplace_back(label.str(), count);
        }
        if(entries.empty())
            return;
        fprintf(fp, "%s", metric_name);
        for (const auto &entry : entries)
            fprintf(fp, ",%s", entry.first.c_str());
        fprintf(fp, "\n");
        fprintf(fp, "%s", metric_name);
        for (const auto &entry : entries)
            fprintf(fp, ",%" PRIu64, entry.second);
        fprintf(fp, "\n");

        // tail latencies
        entries.clear();
        for (size_t i = 0; i < TAIL_BINS; ++i) {
            UInt64 count = tail_bins[i];
            UInt64 range_start = TAIL_START + i * TAIL_W;
            UInt64 range_end = range_start + TAIL_W - 1;
            std::ostringstream label;
            label << "[" << range_start << ".." << range_end << "]";
            entries.emplace_back(label.str(), count);
        }

        fprintf(fp, "%s_tail", metric_name);
        for (const auto &entry : entries)
            fprintf(fp, ",%s", entry.first.c_str());
        fprintf(fp, "\n");
        fprintf(fp, "%s_tail", metric_name);
        for (const auto &entry : entries)
            fprintf(fp, ",%" PRIu64, entry.second);
        fprintf(fp, "\n"); 
    }

    void ProposedHistogram::printCsvCdf(FILE *fp, const char *metric_name) const{
        if(!fp || total == 0)
            return;
        printCsv(fp, metric_name);
        std::vector<std::pair<std::string, UInt64>> entries;
        entries.reserve(kBuckets);
        for (int idx = 0; idx < kBuckets; ++idx){
            UInt64 count = buckets[idx];
            if(!count)
                continue;
            UInt64 range_start = (idx == 0) ? 0 : (UInt64(1) << idx);
            std::ostringstream label;
            label << "[" << range_start << "..";
            if(idx + 1 < kBuckets){
                UInt64 range_end = (UInt64(1) << (idx + 1)) - 1;
                label << range_end << "]";
            } else {
                label << "inf]";
            }
            entries.emplace_back(label.str(), count);
        }
        if(entries.empty())
            return;
        fprintf(fp, "%s_cdf", metric_name);
        for (const auto &entry : entries)
            fprintf(fp, ",%s", entry.first.c_str());
        fprintf(fp, "\n");
        fprintf(fp, "%s_cdf", metric_name);
        UInt64 cumulative = 0;
        for (const auto &entry : entries){
            cumulative += entry.second;
            double pct = static_cast<double>(cumulative) / static_cast<double>(total) * 100.0;
            fprintf(fp, ",%.2f", pct);
        }
        fprintf(fp, "\n");
    }

    namespace {
        void printCsvLabeledCounts(FILE *fp, const char *metric_name, const std::vector<std::pair<std::string, UInt64>> &entries){
            if(!fp || entries.empty())
                return;
            fprintf(fp, "%s", metric_name);
            for (const auto &entry : entries)
                fprintf(fp, ",%s", entry.first.c_str());
            fprintf(fp, "\n");
            fprintf(fp, "%s", metric_name);
            for (const auto &entry : entries)
                fprintf(fp, ",%" PRIu64, entry.second);
            fprintf(fp, "\n");
        }

    }

    PageTableWalkerRadix::PageTableWalkerRadix(int number_of_levels, 
                                                   Core* _core, ShmemPerfModel* _m_shmem_perf_model, 
                                                   int *level_bit_indices,int *level_percentages, PWC* pwc, bool pwc_enabled,UtopiaCache* _shadow_cache)
    :PageTableWalker(_core->getId(), 0, _m_shmem_perf_model, pwc, pwc_enabled)
    {
        if(level_bit_indices!=NULL){
            this->shadow_cache=_shadow_cache;
            this->core =_core;
            this->m_shmem_perf_model=_m_shmem_perf_model;
            this->stats_radix.number_of_levels=number_of_levels;
            this->stats_radix.address_bit_indices=(int *)malloc((number_of_levels+1)*sizeof(int));
            this->stats_radix.hit_percentages=(int *)malloc((number_of_levels+1)*sizeof(int));
            for (int i = 0; i < number_of_levels+1; i++)
            {
                if(i<number_of_levels){
                    this->stats_radix.hit_percentages[i]=level_percentages[i];
                }
                this->stats_radix.address_bit_indices[i]=level_bit_indices[i];
            }
            this->starting_table=InitiateTablePtw((int)pow(2.0,(float)level_bit_indices[0]));
        }
        latency_per_level = new SubsecondTime[number_of_levels];
        for (int i = 0; i < number_of_levels; ++i)
            latency_per_level[i] = SubsecondTime::Zero();
        latency_histograms.resize(number_of_levels);
        hit_where_histograms.resize(number_of_levels);
        hit_where_latency.resize(number_of_levels);
        level_accesses.resize(number_of_levels, 0);
        psc_hits_per_level.resize(number_of_levels, 0);
        psc_misses_per_level.resize(number_of_levels, 0);
        psc_miss_latency_histograms.resize(number_of_levels);
        psc_miss_latency_total_cycles.resize(number_of_levels, 0);
        psc_miss_hit_where_counts.resize(number_of_levels);
        for (auto &counts : psc_miss_hit_where_counts)
            counts.fill(0);
        rob_stall_psc_level_cycles.resize(number_of_levels, 0);
        psc_accesses = 0;
        psc_misses = 0;
        for (auto &row : ptb_pdpt_combo_counts)
            row.fill(0);
        rob_stall_stlb_miss_cycles = 0;
        traversal_paths_unique_count = 0;
        last_psc_miss_level_index = -1;
        last_psc_miss_hitwhere = HitWhere::where_t();
        total_walk_latency = SubsecondTime::Zero();
        total_ptb_latency = SubsecondTime::Zero();
        early_fetch_enabled = Sim()->getCfg()->getBoolDefault("perf_model/ptb/early_fetch", false);
        overlap_samples = 0;
        overlap_ready = 0;
        overlap_ratio_sum_milli = 0;
        overlap_prefetch_state = {false, 0, SubsecondTime::Zero(), SubsecondTime::Zero()};
        name = "ptw_radix_";
        name = name + std::to_string(counter).c_str();
        for (int i = 0; i < number_of_levels; i++){
            String metric_name = "page_level_latency_";
            String metric = metric_name+std::to_string(i).c_str();
            registerStatsMetric(name, core_id, metric, &latency_per_level[i]);
            String psc_hits_metric = String(("psc_hits_level_" + std::to_string(i + 1) + "_proposed").c_str());
            registerStatsMetric(name, core_id, psc_hits_metric, &psc_hits_per_level[i]);
            String psc_misses_metric = String(("psc_misses_level_" + std::to_string(i + 1) + "_proposed").c_str());
            registerStatsMetric(name, core_id, psc_misses_metric, &psc_misses_per_level[i]);
            String psc_latency_metric = String(("psc_miss_latency_histogram_level_" + std::to_string(i + 1) + "_proposed").c_str());
            // registerStatsMetric(name, core_id, psc_latency_metric, &psc_miss_latency_histograms[i]);
            String rob_stall_psc_metric = String(("rob_stall_psc_level_" + std::to_string(i + 1) + "_cycles").c_str());
            registerStatsMetric(name, core_id, rob_stall_psc_metric, &rob_stall_psc_level_cycles[i]);
            // for (int where = 0; where < HitWhere::NUM_HITWHERES; ++where){
            //     HitWhere::where_t where_type = static_cast<HitWhere::where_t>(where);
            //     String where_name = String(HitWhereString(where_type));
            //     String psc_hitwhere_metric = String(("psc_miss_hitwhere_" + std::string(where_name.c_str()) + "_level_" + std::to_string(i + 1) + "_proposed").c_str());
            //     registerStatsMetric(name, core_id, psc_hitwhere_metric, &psc_miss_hit_where_counts[i][where]);
            // }
        }
        registerStatsMetric(name, core_id, "psc_accesses_proposed", &psc_accesses);
        registerStatsMetric(name, core_id, "psc_misses_total_proposed", &psc_misses);
        registerStatsMetric(name, core_id, "rob_stall_stlb_miss_cycles", &rob_stall_stlb_miss_cycles);
        registerStatsMetric(name, core_id, "ptw_traversal_paths_unique_proposed", &traversal_paths_unique_count);
        // registerStatsMetric(name, core_id, "tlb_miss_service_latency_histogram_proposed", &stlb_miss_latency_histogram);
        
        counter++;

        
    }

    SubsecondTime PageTableWalkerRadix::init_walk(IntPtr eip, IntPtr address,
        UtopiaCache* shadow_cache,
        CacheCntlr *_cache,
        Core::lock_signal_t lock_signal,
        Byte* data_buf, UInt32 data_length,
        bool modeled, bool count){

            addresses.clear();
            cache = _cache;
            stats.page_walks++;
            overlap_prefetch_state.valid = false;

            std::vector<uint64_t> vpn_indices = computeVpnIndices(address);

            SubsecondTime total_latency;
            SubsecondTime t_start;
            SubsecondTime now = getShmemPerfModel()->getElapsedTime(ShmemPerfModel::_USER_THREAD);

            SubsecondTime ptb_latency = SubsecondTime::Zero();
            std::string traversal_path = "DTLB->STLB->PTW";
            auto append_psc_event = [&](int level, const std::string &event) {
                traversal_path += "->PSC-L" + std::to_string(level) + "-" + event;
            };
            size_t combo_levels = std::min<size_t>(stats_radix.number_of_levels, 4);
            PscCombinationState psc_state(combo_levels);
            auto record_combination = [&]() {
                if(!count || !page_walk_cache_enabled)
                    return;
                bool complete = true;
                for(char outcome : psc_state.outcomes){
                    if(outcome == '?'){
                        complete = false;
                        break;
                    }
                }
                if(!complete)
                    return;
                // C++11 COMPATIBLE VERSION
                std::string key(psc_state.outcomes.begin(), psc_state.outcomes.end());

                // Emplace returns a std::pair<iterator, bool> in C++11
                auto emplace_result = psc_combination_hitwhere_counts.emplace(
                    key, std::array<UInt64, HitWhere::NUM_HITWHERES + 1>{});

                // Extract the iterator and the boolean flag manually from the pair
                auto it = emplace_result.first;
                bool inserted = emplace_result.second;

                auto &counts = it->second;
                if(inserted) {
                    counts.fill(0);
                }

                size_t index = psc_state.any_miss ? static_cast<size_t>(psc_state.miss_hitwhere) : HitWhere::NUM_HITWHERES;

                if(index < counts.size()) {
                    counts[index]++;
                }
            };
            // Pravesh:1 Track ROB stall cycles for STLB-miss translation, and split by PSC level.
            auto record_rob_stall_cycles = [&](SubsecondTime latency) {
                if (!count)
                    return;
                rob_stall_stlb_miss_cycles += SubsecondTime::divideRounded(latency, core->getDvfsDomain()->getPeriod());
            };
            auto record_traversal_path = [&](const std::string &path) {
                auto it = traversal_path_counts.find(path);
                if(it == traversal_path_counts.end()){
                    auto inserted = traversal_path_counts.insert(std::make_pair(path, 0));
                    it = inserted.first;
                    traversal_paths_unique_count++;
                }
                it->second++;
            };
            last_psc_miss_level_index = -1;
            
            bool ptb_hit = false;
            if(ptb){
                PageTableBuffer::LookupResult lookup_result = ptb->lookup(vpn_indices, count);
                ptb_latency = lookup_result.latency;
                ptb_hit = lookup_result.hit;
                if(lookup_result.hit){
                    int start_level = (ptb->getMode() == PageTableBuffer::Mode::LEAF_PT) ? stats_radix.number_of_levels : stats_radix.number_of_levels - 1;
                    ptw_table* start_table = reinterpret_cast<ptw_table*>(lookup_result.base_address);
                    if(count)
                        traversal_path += "->PTB-HIT-L" + std::to_string(start_level);
                    if(count && page_walk_cache_enabled && pwc){
                        IntPtr pml4_address = (IntPtr)(&starting_table->entries[vpn_indices[0]]);
                        bool pml4_hit = (pwc->probe(pml4_address, 1) == PWC::HIT);
                        updatePscCombinationState(&psc_state, 0, pml4_hit, HitWhere::UNKNOWN, !pml4_hit);
                        bool pdpt_hit = false;
                        ptw_table* pdpt_table = resolveTableForLevel(vpn_indices, 2);
                        if(pdpt_table){
                            IntPtr pdpt_address = (IntPtr)(&pdpt_table->entries[vpn_indices[1]]);
                            pdpt_hit = (pwc->probe(pdpt_address, 2) == PWC::HIT);
                        }
                        updatePscCombinationState(&psc_state, 1, pdpt_hit, HitWhere::UNKNOWN, !pdpt_hit);
                        recordPtbPdptCombo(true, pdpt_hit);
                    }
                    SubsecondTime walk_latency = InitializeWalkRecursive(eip, address, start_level, start_table, lock_signal, data_buf, data_length, modeled, count, traversal_path, true, &psc_state, ptb_hit);
                    SubsecondTime final_latency = ptb_latency + walk_latency;
                    total_ptb_latency += ptb_latency;
                    total_walk_latency += final_latency;
                    stlb_miss_latency_histogram.update(SubsecondTime::divideRounded(final_latency, core->getDvfsDomain()->getPeriod()));
                    record_rob_stall_cycles(final_latency);
                    m_shmem_perf_model->setElapsedTime(ShmemPerfModel::_USER_THREAD,now);
                    UInt64 vpn = address >> init_walk_functional(address);
                    track_per_page_ptw_latency(vpn,final_latency);
                    if(count)
                        record_traversal_path(traversal_path);
                    record_combination();
                    return final_latency;
                }
                total_ptb_latency += ptb_latency;
            }

            uint64_t a1 = vpn_indices[0];
            bool pwc_hit = false;

            int level_index = 0;
            if(page_walk_cache_enabled){ //@kanellok access page walk caches

                            PWC::where_t pwc_where;

                            if(page_walk_cache_enabled)
                {
                    IntPtr pwc_address = (IntPtr)(&starting_table->entries[a1]);
                    pwc_where = pwc->lookup(pwc_address, t_start ,true, 1, count);
                    if(count)
                        psc_accesses++;
                    if( pwc_where == PWC::HIT ) pwc_hit = true;

                }

            }

            bool level0_recorded = false;
            bool level_recorded = false;
            if(pwc_hit == true){

                    total_latency = pwc->access_latency.getLatency();
                    if(count)
                        psc_hits_per_level[level_index]++;
                    if(count)
                        append_psc_event(level_index + 1, "HIT");
                    if(page_walk_cache_enabled)
                        updatePscCombinationState(&psc_state, level_index, true, HitWhere::where_t(), false);

            }
            else{

                    t_start = getShmemPerfModel()->getElapsedTime(ShmemPerfModel::_USER_THREAD);

                    IntPtr cache_address = ((IntPtr)(&starting_table->entries[a1])) & (~((64 - 1)));

                    HitWhere::where_t hit_where = cache->processMemOpFromCore(
                        eip,
                        lock_signal,
                        Core::mem_op_t::READ,
                        cache_address, 0,
                        data_buf, data_length,
                        modeled,
                        count, CacheBlockInfo::block_type_t::PAGE_TABLE, SubsecondTime::Zero(),shadow_cache);


                    addresses.push_back((IntPtr)(&starting_table->entries[a1]));

                    SubsecondTime t_end = getShmemPerfModel()->getElapsedTime(ShmemPerfModel::_USER_THREAD);
                    if(page_walk_cache_enabled)
                        total_latency = t_end - t_start + pwc->miss_latency.getLatency();
                    else
                        total_latency = t_end - t_start;

                    m_shmem_perf_model->setElapsedTime(ShmemPerfModel::_USER_THREAD,now);


                    mem_manager->tagCachesBlockType(cache_address,CacheBlockInfo::block_type_t::PAGE_TABLE);

                    recordLevelStats(0, total_latency, &hit_where);
                    if(page_walk_cache_enabled && count){
                        recordPscMiss(level_index, total_latency, hit_where);
                    }
                    if(page_walk_cache_enabled)
                        updatePscCombinationState(&psc_state, level_index, false, hit_where, true);
                    if(count){
                        if(page_walk_cache_enabled)
                            append_psc_event(level_index + 1, std::string("MISS-") + HitWhereString(hit_where));
                        else
                            append_psc_event(level_index + 1, "DISABLED");
                    }
                    level0_recorded = true;

            }

            if(!level0_recorded)
                recordLevelStats(0, total_latency);


            if(starting_table->entries[a1].entry_type==ptw_table_entry_type::PTW_NONE){
                starting_table->entries[a1]=*CreateNewPtwEntryAtLevel(1,stats_radix.number_of_levels,stats_radix.address_bit_indices,stats_radix.hit_percentages,this,address);
            }
            if(starting_table->entries[a1].entry_type==ptw_table_entry_type::PTW_ADDRESS){
                //std::cout<<std::hex<<address<<" - "<<std::hex<<a1<<" - "<<level<<" Address\n";
                SubsecondTime final_latency = total_latency + ptb_latency;
                stlb_miss_latency_histogram.update(SubsecondTime::divideRounded(final_latency, core->getDvfsDomain()->getPeriod()));
                record_rob_stall_cycles(final_latency);
                if(count)
                    record_traversal_path(traversal_path);
                record_combination();
                return final_latency;
            }


            SubsecondTime final_latency = ptb_latency + total_latency+InitializeWalkRecursive(eip, address,2,starting_table->entries[a1].next_level_table,lock_signal,data_buf,data_length, modeled, count, traversal_path, true, &psc_state, ptb_hit);

            if(ptb){
                PageTableBuffer::Mode mode = ptb->getMode();
                int target_level = (mode == PageTableBuffer::Mode::LEAF_PT) ? stats_radix.number_of_levels : stats_radix.number_of_levels - 1;
                ptw_table* target_table = resolveTableForLevel(vpn_indices, target_level);
                if(target_table)
                    ptb->insert(vpn_indices, reinterpret_cast<IntPtr>(target_table));
            }

            m_shmem_perf_model->setElapsedTime(ShmemPerfModel::_USER_THREAD,now);
            UInt64 vpn = address >> init_walk_functional(address);
            track_per_page_ptw_latency(vpn,final_latency);
            total_walk_latency += final_latency;
            stlb_miss_latency_histogram.update(SubsecondTime::divideRounded(final_latency, core->getDvfsDomain()->getPeriod()));
            record_rob_stall_cycles(final_latency);
            if(count)
                record_traversal_path(traversal_path);
            record_combination();


            return final_latency;

    }

    SubsecondTime PageTableWalkerRadix::InitializeWalkRecursive(IntPtr eip, IntPtr address,
        int level,ptw_table* new_table,
        Core::lock_signal_t lock_signal,
        Byte* data_buf, UInt32 data_length,
        bool modeled, bool count, std::string &traversal_path, bool allow_psc_lookup, PscCombinationState *psc_state, bool ptb_hit){

            uint64_t a1;
            int shift_bits=0;
            IntPtr pwc_address;
            SubsecondTime t_start;
            SubsecondTime total_latency;
            HitWhere::where_t pd_hit_where = HitWhere::UNKNOWN;
            
            for (int i = stats_radix.number_of_levels; i >= level; i--)
            {
                shift_bits+=stats_radix.address_bit_indices[i];
            }

            a1=((address>>shift_bits))&0x1ff;

            bool pwc_hit = false;

            int level_index = level - 1;
            if(page_walk_cache_enabled && allow_psc_lookup){ //@kanellok access page walk caches 

			    PWC::where_t pwc_where;

			    if(page_walk_cache_enabled && allow_psc_lookup && level != (stats_radix.number_of_levels) )
                {
                    pwc_address = (IntPtr)(&new_table->entries[a1]);
                    pwc_where = pwc->lookup(pwc_address, t_start ,true, level, count);
                    if(count)
                        psc_accesses++;
                    if( pwc_where == PWC::HIT ) pwc_hit = true; 

                }
            }
		
            if(pwc_hit == true){

                    total_latency = pwc->access_latency.getLatency(); 
                    if(count)
                        psc_hits_per_level[level_index]++;
                    if(count)
                        traversal_path += "->PSC-L" + std::to_string(level_index + 1) + "-HIT";
                    if(page_walk_cache_enabled)
                        updatePscCombinationState(psc_state, level_index, true, HitWhere::where_t(), false);
                    recordLevelStats(level-1, total_latency);
                    if(count && page_walk_cache_enabled && allow_psc_lookup && level_index == 1)
                        recordPtbPdptCombo(ptb_hit, true);
            }
            else{
                    
                    t_start = getShmemPerfModel()->getElapsedTime(ShmemPerfModel::_USER_THREAD);
                    
                    IntPtr cache_address = ((IntPtr)(&new_table->entries[a1])) & (~((64 - 1))); 
                    if(count && overlap_prefetch_state.valid
                        && level == stats_radix.number_of_levels
                        && cache_address == overlap_prefetch_state.leaf_cache_line){
                        SubsecondTime t_need = getShmemPerfModel()->getElapsedTime(ShmemPerfModel::_USER_THREAD);
                        SubsecondTime t_issue = overlap_prefetch_state.t_issue;
                        SubsecondTime t_done = overlap_prefetch_state.t_done;
                        UInt64 pte_cycles = (t_done > t_issue)
                            ? SubsecondTime::divideRounded(t_done - t_issue, core->getDvfsDomain()->getPeriod())
                            : 0;
                        if(pte_cycles > 0){
                            UInt64 tail_cycles = (t_done > t_need)
                                ? SubsecondTime::divideRounded(t_done - t_need, core->getDvfsDomain()->getPeriod())
                                : 0;
                            UInt64 overlap_cycles = (pte_cycles > tail_cycles) ? (pte_cycles - tail_cycles) : 0;
                            UInt64 ratio_milli = static_cast<UInt64>((overlap_cycles * 1000ULL) / pte_cycles);
                            overlap_ratio_histogram.update(ratio_milli);
                            overlap_tail_latency_histogram.update(tail_cycles);
                            overlap_ratio_sum_milli += ratio_milli;
                            overlap_samples++;
                            if(t_done <= t_need)
                                overlap_ready++;
                        }
                        overlap_prefetch_state.valid = false;
                    }

                    HitWhere::where_t hit_where = cache->processMemOpFromCore(
                        eip,
                        lock_signal,
                        Core::mem_op_t::READ,
                        cache_address, 0,
                        data_buf, data_length,
                        modeled,
                        count, CacheBlockInfo::block_type_t::PAGE_TABLE, SubsecondTime::Zero());

                    SubsecondTime t_end = getShmemPerfModel()->getElapsedTime(ShmemPerfModel::_USER_THREAD);
                    
                    if(page_walk_cache_enabled && allow_psc_lookup)
                        total_latency = t_end - t_start + pwc->miss_latency.getLatency();
                    else
                        total_latency = t_end - t_start;
                    
                    addresses.push_back((IntPtr)(&new_table->entries[a1]));

                    mem_manager->tagCachesBlockType(cache_address,CacheBlockInfo::block_type_t::PAGE_TABLE);
                    recordLevelStats(level-1, total_latency, &hit_where);
                    if(level_index == stats_radix.number_of_levels - 2)
                        pd_hit_where = hit_where;
                    if(page_walk_cache_enabled && count){
                        recordPscMiss(level_index, total_latency, hit_where);
                    }
                    if(page_walk_cache_enabled)
                        updatePscCombinationState(psc_state, level_index, false, hit_where, true);
                    if(count){
                        if(page_walk_cache_enabled && allow_psc_lookup)
                            traversal_path += "->PSC-L" + std::to_string(level_index + 1) + "-MISS-" + HitWhereString(hit_where);
                        else
                            traversal_path += "->PSC-L" + std::to_string(level_index + 1) + "-DISABLED";
                    }
                    if(count && page_walk_cache_enabled && allow_psc_lookup && level_index == 1)
                        recordPtbPdptCombo(ptb_hit, false);

            }

            if(new_table->entries[a1].entry_type==ptw_table_entry_type::PTW_NONE){
                new_table->entries[a1]=*CreateNewPtwEntryAtLevel(level,stats_radix.number_of_levels,stats_radix.address_bit_indices,stats_radix.hit_percentages,this, address);
            }
            if(new_table->entries[a1].entry_type==ptw_table_entry_type::PTW_ADDRESS){
                //std::cout<<std::hex<<address<<" - "<<std::hex<<a1<<" - "<<level<<" Address\n";
                return total_latency;
            }
            
            bool pd_level = (level_index == stats_radix.number_of_levels - 2);
            bool pd_psc_miss = early_fetch_enabled && pd_level && !pwc_hit;

            // Prefetch the leaf PTE after a PD-level PSC miss (hit or page-fault path).
            if (pd_psc_miss
                && new_table->entries[a1].entry_type == ptw_table_entry_type::PTW_TABLE_POINTER
                && new_table->entries[a1].next_level_table)
            {
                CacheCntlr* prefetch_cache = cache;
                if(mem_manager){
                    switch (pd_hit_where){
                        case HitWhere::L1_OWN:
                            prefetch_cache = mem_manager->getCacheCntlrAt(core->getId(), MemComponent::L1_DCACHE);
                            break;
                        case HitWhere::L2_OWN:
                            prefetch_cache = mem_manager->getCacheCntlrAt(core->getId(), MemComponent::L2_CACHE);
                            break;
                        case HitWhere::L3_OWN:
                            prefetch_cache = mem_manager->getCacheCntlrAt(core->getId(), MemComponent::L3_CACHE);
                            break;
                        case HitWhere::L4_OWN:
                            prefetch_cache = mem_manager->getCacheCntlrAt(core->getId(), MemComponent::L4_CACHE);
                            break;
                        case HitWhere::DRAM:
                        case HitWhere::DRAM_LOCAL:
                        case HitWhere::DRAM_REMOTE:
                        case HitWhere::DRAM_CACHE:
                        case HitWhere::MISS:
                        case HitWhere::NUCA_CACHE:
                        case HitWhere::CACHE_REMOTE:
                        case HitWhere::SIBLING:
                        case HitWhere::L1_SIBLING:
                        case HitWhere::L2_SIBLING:
                        case HitWhere::L3_SIBLING:
                        case HitWhere::L4_SIBLING:
                        default:
                            prefetch_cache = mem_manager->getCacheCntlrAt(core->getId(), MemComponent::LAST_LEVEL_CACHE);
                            break;
                    }
                }
                if(!prefetch_cache)
                    prefetch_cache = cache;
                std::vector<uint64_t> vpn_indices = computeVpnIndices(address);
                uint64_t leaf_index = vpn_indices.back();
                ptw_table* leaf_table = new_table->entries[a1].next_level_table;
                IntPtr leaf_address = ((IntPtr)(&leaf_table->entries[leaf_index])) & (~((64 - 1)));
                SubsecondTime prefetch_time = getShmemPerfModel()->getElapsedTime(ShmemPerfModel::_USER_THREAD);
                HitWhere::where_t res = prefetch_cache->processMemOpFromCore(
                    eip,
                    lock_signal,
                    Core::mem_op_t::READ,
                    leaf_address, 0,
                    data_buf, data_length,
                    true,
                    false, CacheBlockInfo::block_type_t::PAGE_TABLE, SubsecondTime::Zero());
                pwc->lookup(leaf_address, prefetch_time, true, level + 1, false);

                SubsecondTime prefetch_done = getShmemPerfModel()->getElapsedTime(ShmemPerfModel::_USER_THREAD);
                uint64_t delta = SubsecondTime::divideRounded(prefetch_done - prefetch_time, core->getDvfsDomain()->getPeriod());
                prefeth_latency[res].update(delta);
                if(count){
                    overlap_prefetch_state.valid = true;
                    overlap_prefetch_state.leaf_cache_line = leaf_address;
                    overlap_prefetch_state.t_issue = prefetch_time;
                    overlap_prefetch_state.t_done = prefetch_done;
                }

                m_shmem_perf_model->setElapsedTime(ShmemPerfModel::_USER_THREAD, prefetch_time);
            }

            return total_latency+InitializeWalkRecursive(eip,address,level+1,new_table->entries[a1].next_level_table,lock_signal,data_buf,data_length,modeled,count, traversal_path, allow_psc_lookup && !pd_psc_miss, psc_state, ptb_hit);
        
    }
    void PageTableWalkerRadix::recordPscMiss(int level_index, SubsecondTime latency, HitWhere::where_t hit_where){
        UInt64 cycles = SubsecondTime::divideRounded(latency, core->getDvfsDomain()->getPeriod());
        psc_misses++;
        psc_misses_per_level[level_index]++;
        psc_miss_latency_histograms[level_index].update(cycles);
        psc_miss_hit_where_counts[level_index][hit_where]++;
        psc_miss_latency_total_cycles[level_index] += cycles;
        rob_stall_psc_level_cycles[level_index] += cycles;
        if(last_psc_miss_level_index >= 0){
            std::string pair_label = "L" + std::to_string(last_psc_miss_level_index + 1)
                + "->L" + std::to_string(level_index + 1)
                + ":" + std::string(HitWhereString(last_psc_miss_hitwhere))
                + "->" + std::string(HitWhereString(hit_where));
            psc_miss_hitwhere_pair_counts[pair_label]++;
        }
        last_psc_miss_level_index = level_index;
        last_psc_miss_hitwhere = hit_where;
    }

    void PageTableWalkerRadix::recordPtbPdptCombo(bool ptb_hit, bool pdpt_hit){
        size_t ptb_index = ptb_hit ? 1 : 0;
        size_t pdpt_index = pdpt_hit ? 1 : 0;
        ptb_pdpt_combo_counts[ptb_index][pdpt_index]++;
    }

    void PageTableWalkerRadix::snapshotPscStats(std::vector<UInt64> &hits,
                                                std::vector<UInt64> &misses,
                                                std::vector<std::array<UInt64, HitWhere::NUM_HITWHERES>> &hitwhere) const{
        hits = psc_hits_per_level;
        misses = psc_misses_per_level;
        hitwhere.assign(psc_miss_hit_where_counts.size(), {});
        for (size_t level = 0; level < psc_miss_hit_where_counts.size(); ++level){
            hitwhere[level].fill(0);
            const auto &map = hit_where_histograms[level];
            for (const auto &entry : map){
                hitwhere[level][entry.first] = entry.second;
            }
        }
    }

    void PageTableWalkerRadix::updatePscCombinationState(PscCombinationState *psc_state, int level_index, bool hit, HitWhere::where_t hit_where, bool has_hitwhere){
        if(!psc_state)
            return;
        if(level_index < 0 || level_index >= static_cast<int>(psc_state->outcomes.size()))
            return;
        psc_state->outcomes[level_index] = hit ? 'H' : 'M';
        if(!hit && has_hitwhere){
            psc_state->miss_hitwhere = static_cast<int>(hit_where);
            psc_state->any_miss = true;
        }
    }
    int PageTableWalkerRadix::init_walk_functional(IntPtr address){
        uint64_t a1;
        int shift_bits=0;
        //std::cout << "Address  = " << address << "Number of levels" << stats_radix.number_of_levels << std::endl;
        
        for (int i = stats_radix.number_of_levels; i >= 1; i--)
        {
            shift_bits+=stats_radix.address_bit_indices[i];
        }
        a1=((address>>shift_bits))&0x1ff;
        if(starting_table->entries[a1].entry_type==ptw_table_entry_type::PTW_NONE){
            starting_table->entries[a1]=*CreateNewPtwEntryAtLevel(1,stats_radix.number_of_levels,stats_radix.address_bit_indices,stats_radix.hit_percentages,this, address);
        }
        if(starting_table->entries[a1].entry_type==ptw_table_entry_type::PTW_ADDRESS){
            
                int page_size=0;
                for(int i=stats_radix.number_of_levels;i>0;i--){
                    page_size+=stats_radix.address_bit_indices[i];
                }
                return (int)(page_size);
        }
        return init_walk_recursive_functional(address,2,starting_table->entries[a1].next_level_table);
    }
    int PageTableWalkerRadix::init_walk_recursive_functional(uint64_t address,int level,ptw_table* new_table){
        uint64_t a1;
        int shift_bits=0;
       // std::cout << "Level  = " << level << std::endl;
        for (int i = stats_radix.number_of_levels; i >= level; i--)
        {
            shift_bits+=stats_radix.address_bit_indices[i];
        }
        a1=((address>>shift_bits))&0x1ff;

       // std::cout << "EntryType = " << new_table->entries[a1].entry_type << std::endl;

        if(new_table->entries[a1].entry_type==ptw_table_entry_type::PTW_NONE){
            new_table->entries[a1]=*CreateNewPtwEntryAtLevel(level,stats_radix.number_of_levels,stats_radix.address_bit_indices,stats_radix.hit_percentages,this, address);
        }
        if(new_table->entries[a1].entry_type==ptw_table_entry_type::PTW_ADDRESS){
            int page_size=0;
            for(int i=stats_radix.number_of_levels;i>level-1;i--){
                page_size+=stats_radix.address_bit_indices[i];
            }
            return (int)(page_size);
            
        }
        return init_walk_recursive_functional(address,level+1,new_table->entries[a1].next_level_table);
    }

    bool PageTableWalkerRadix::isPageFault(IntPtr address){
        uint64_t a1;
        int shift_bits=0;
        //std::cout << "Address  = " << address << "Number of levels" << stats_radix.number_of_levels << std::endl;
        
        for (int i = stats_radix.number_of_levels; i >= 1; i--)
        {
            shift_bits+=stats_radix.address_bit_indices[i];
        }
        a1=((address>>shift_bits))&0x1ff;

        if(starting_table->entries[a1].entry_type==ptw_table_entry_type::PTW_NONE){
            return true;
        }
        if(starting_table->entries[a1].entry_type==ptw_table_entry_type::PTW_ADDRESS){
            return false;
        }

        return isPageFaultHelper(address,2,starting_table->entries[a1].next_level_table);


    }

    bool PageTableWalkerRadix::isPageFaultHelper(uint64_t address,int level,ptw_table* new_table){

        uint64_t a1;
        int shift_bits=0;
       // std::cout << "Level  = " << level << std::endl;
        for (int i = stats_radix.number_of_levels; i >= level; i--)
        {
            shift_bits+=stats_radix.address_bit_indices[i];
        }
        a1=((address>>shift_bits))&0x1ff;

       // std::cout << "EntryType = " << new_table->entries[a1].entry_type << std::endl;

        if(new_table->entries[a1].entry_type==ptw_table_entry_type::PTW_NONE){
            return true;
        }
        if(new_table->entries[a1].entry_type==ptw_table_entry_type::PTW_ADDRESS){

            return false;
            
        }
        return isPageFaultHelper(address,level+1,new_table->entries[a1].next_level_table);

    }

    std::vector<uint64_t> PageTableWalkerRadix::computeVpnIndices(uint64_t address){
        std::vector<uint64_t> indices;
        indices.reserve(stats_radix.number_of_levels);

        for (int level = 1; level <= stats_radix.number_of_levels; level++)
        {
            int shift_bits = 0;
            for (int i = stats_radix.number_of_levels; i >= level; i--)
            {
                shift_bits += stats_radix.address_bit_indices[i];
            }
            indices.push_back((address >> shift_bits) & 0x1ff);
        }

        return indices;
    }

    ptw_table* PageTableWalkerRadix::resolveTableForLevel(const std::vector<uint64_t> &vpn_indices, int target_level){
        if(target_level <= 1 || target_level > stats_radix.number_of_levels)
            return NULL;

        ptw_table* current_table = starting_table;

        for (int level = 1; level < target_level; level++)
        {
            uint64_t index = vpn_indices[level-1];
            if(current_table->entries[index].entry_type != ptw_table_entry_type::PTW_TABLE_POINTER ||
               current_table->entries[index].next_level_table == NULL)
            {
                return NULL;
            }
            current_table = current_table->entries[index].next_level_table;
        }

        return current_table;
    }

    void PageTableWalkerRadix::recordLevelStats(int level_index, SubsecondTime latency, HitWhere::where_t *hit_where){
        if(level_index < 0 || level_index >= stats_radix.number_of_levels)
            return;

        latency_per_level[level_index] += latency;
        latency_histograms[level_index].update(latency.getNS());
        level_accesses[level_index]++;

        if(hit_where){
            hit_where_histograms[level_index][*hit_where]++;
            hit_where_latency[level_index][*hit_where] += latency;
        }
    }

    PageTableWalkerRadix::~PageTableWalkerRadix(){
        UInt64 walks = stats.page_walks;
        SubsecondTime period = core->getDvfsDomain()->getPeriod();
        UInt64 instruction_count = core->getInstructionCount();
        double stall_cycles_per_instruction = instruction_count
            ? static_cast<double>(rob_stall_stlb_miss_cycles) / static_cast<double>(instruction_count)
            : 0.0;
        double cpi_on_stlb_miss = 1.0 + stall_cycles_per_instruction;
        double avg_stall_cycles = walks ? static_cast<double>(SubsecondTime::divideRounded(total_walk_latency, period)) / walks : 0.0;

        String stats_output_path = Sim()->getConfig()->formatOutputFileName("proposed.stats");
        FILE *stats_fp = fopen(stats_output_path.c_str(), "a");
        if(stats_fp){
            fprintf(stats_fp, "[Core %d] proposed STLB miss CPI: %.4f (stall cycles per instruction %.6f over %" PRIu64 " instructions)\n",
                    core_id, cpi_on_stlb_miss, stall_cycles_per_instruction, instruction_count);
            if(psc_accesses > 0){
                double psc_miss_rate = (static_cast<double>(psc_misses) / static_cast<double>(psc_accesses)) * 100.0;
                fprintf(stats_fp, "[Core %d] proposed PSC miss rate: %.2f%% (%" PRIu64 "/%" PRIu64 ")\n",
                        core_id, psc_miss_rate, psc_misses, psc_accesses);
                UInt64 total_miss_cycles = 0;
                for (UInt64 level_cycles : psc_miss_latency_total_cycles)
                    total_miss_cycles += level_cycles;
                for (int lvl = 0; lvl < stats_radix.number_of_levels; ++lvl){
                    fprintf(stats_fp, "  proposed PSC level %d hits %" PRIu64 ", misses %" PRIu64 "\n",
                            lvl+1, psc_hits_per_level[lvl], psc_misses_per_level[lvl]);
                    double avg_miss_latency = psc_misses_per_level[lvl]
                        ? static_cast<double>(psc_miss_latency_total_cycles[lvl]) / static_cast<double>(psc_misses_per_level[lvl])
                        : 0.0;
                    double miss_share = total_miss_cycles
                        ? static_cast<double>(psc_miss_latency_total_cycles[lvl]) / static_cast<double>(total_miss_cycles) * 100.0
                        : 0.0;
                    fprintf(stats_fp, "  proposed PSC level %d avg miss latency (cycles): %.2f\n",
                            lvl+1, avg_miss_latency);
                    fprintf(stats_fp, "  proposed PSC level %d miss latency share: %.2f%%\n",
                            lvl+1, miss_share);
                    String label = String(("  proposed PSC level " + std::to_string(lvl + 1) + " miss latency histogram (cycles)").c_str());
                    psc_miss_latency_histograms[lvl].print(stats_fp, label.c_str());
                    bool printed_hitwhere = false;
                    for (int where = 0; where < HitWhere::NUM_HITWHERES; ++where){
                        UInt64 count = psc_miss_hit_where_counts[lvl][where];
                        if(!count)
                            continue;
                        if(!printed_hitwhere){
                            fprintf(stats_fp, "    proposed PSC level %d miss HitWhere histogram:\n", lvl+1);
                            printed_hitwhere = true;
                        }
                        fprintf(stats_fp, "      %s: %" PRIu64 "\n", HitWhereString(static_cast<HitWhere::where_t>(where)), count);
                    }
                }
            }
            if(!psc_combination_hitwhere_counts.empty()){
                fprintf(stats_fp, "  proposed PSC hit/miss combinations by HitWhere:\n");
                for (const auto &entry : psc_combination_hitwhere_counts){
                    fprintf(stats_fp, "    %s:", entry.first.c_str());
                    fprintf(stats_fp, " None=%" PRIu64, entry.second[HitWhere::NUM_HITWHERES]);
                    for (int where = 0; where < HitWhere::NUM_HITWHERES; ++where){
                        fprintf(stats_fp, " %s=%" PRIu64,
                                HitWhereString(static_cast<HitWhere::where_t>(where)),
                                entry.second[where]);
                    }
                    fprintf(stats_fp, "\n");
                }
            }
            if(!psc_miss_hitwhere_pair_counts.empty()){
                fprintf(stats_fp, "  proposed PSC miss HitWhere pairs:\n");
                for (const auto &entry : psc_miss_hitwhere_pair_counts)
                    fprintf(stats_fp, "    %s: %" PRIu64 "\n", entry.first.c_str(), entry.second);
            }
            UInt64 ptb_pdpt_total = 0;
            for (const auto &row : ptb_pdpt_combo_counts){
                for (UInt64 count : row)
                    ptb_pdpt_total += count;
            }
            if(ptb_pdpt_total > 0){
                fprintf(stats_fp, "  proposed PTB/PDPT hit combinations:\n");
                fprintf(stats_fp, "    PTB-MISS PDPT-MISS: %" PRIu64 "\n", ptb_pdpt_combo_counts[0][0]);
                fprintf(stats_fp, "    PTB-MISS PDPT-HIT: %" PRIu64 "\n", ptb_pdpt_combo_counts[0][1]);
                fprintf(stats_fp, "    PTB-HIT PDPT-MISS: %" PRIu64 "\n", ptb_pdpt_combo_counts[1][0]);
                fprintf(stats_fp, "    PTB-HIT PDPT-HIT: %" PRIu64 "\n", ptb_pdpt_combo_counts[1][1]);
            }
            if(!traversal_path_counts.empty()){
                fprintf(stats_fp, "[Core %d] proposed PTW traversal paths (%" PRIu64 "):\n", core_id, traversal_paths_unique_count);
                for(const auto &entry : traversal_path_counts){
                    fprintf(stats_fp, "  %s: %" PRIu64 "\n", entry.first.c_str(), entry.second);
                }
            }
            String tlb_label(("[Core " + std::to_string(core_id) + "] proposed TLB miss service latency histogram (cycles)").c_str());
            stlb_miss_latency_histogram.print(stats_fp, tlb_label.c_str());
            double total_ns = static_cast<double>(total_walk_latency.getNS());
            if(total_ns > 0){
                double ptb_share = static_cast<double>(total_ptb_latency.getNS()) / total_ns * 100.0;
                fprintf(stats_fp, "[Core %d] proposed PTB latency share: %.2f%%\n", core_id, ptb_share);
            }
            if(overlap_samples > 0){
                double avg_overlap_ratio = static_cast<double>(overlap_ratio_sum_milli) / static_cast<double>(overlap_samples) / 1000.0;
                double overlap_ready_pct = static_cast<double>(overlap_ready) / static_cast<double>(overlap_samples) * 100.0;
                fprintf(stats_fp, "[Core %d] proposed PTB overlap ratio avg: %.4f (samples %" PRIu64 ")\n",
                        core_id, avg_overlap_ratio, overlap_samples);
                fprintf(stats_fp, "[Core %d] proposed PTB overlap ready rate: %.2f%% (%" PRIu64 "/%" PRIu64 ")\n",
                        core_id, overlap_ready_pct, overlap_ready, overlap_samples);
            }
            fclose(stats_fp);
        }

        String csv_output_path = Sim()->getConfig()->formatOutputFileName("proposed.csv");
        FILE *csv_fp = fopen(csv_output_path.c_str(), "a");
        if(csv_fp){
            fprintf(csv_fp, "proposed_STLB_miss_CPI,%.4f\n", cpi_on_stlb_miss);
            fprintf(csv_fp, "proposed_STLB_miss_stall_cycles_per_instruction,%.6f\n", stall_cycles_per_instruction);
            fprintf(csv_fp, "proposed_STLB_miss_avg_stall_cycles,%.6f\n", avg_stall_cycles);
            fprintf(csv_fp, "proposed_STLB_miss_instruction_count,%" PRIu64 "\n", instruction_count);
            fprintf(csv_fp, "proposed_STLB_miss_walks,%" PRIu64 "\n", walks);
            if(psc_accesses > 0){
                double psc_miss_rate = (static_cast<double>(psc_misses) / static_cast<double>(psc_accesses)) * 100.0;
                fprintf(csv_fp, "proposed_PSC_miss_rate_pct,%.2f\n", psc_miss_rate);
                fprintf(csv_fp, "proposed_PSC_misses,%" PRIu64 "\n", psc_misses);
                fprintf(csv_fp, "proposed_PSC_accesses,%" PRIu64 "\n", psc_accesses);
                UInt64 total_miss_cycles = 0;
                for (UInt64 level_cycles : psc_miss_latency_total_cycles)
                    total_miss_cycles += level_cycles;
                for (int lvl = 0; lvl < stats_radix.number_of_levels; ++lvl){
                    fprintf(csv_fp, "proposed_PSC_L%d_hits,%" PRIu64 "\n", lvl + 1, psc_hits_per_level[lvl]);
                    fprintf(csv_fp, "proposed_PSC_L%d_misses,%" PRIu64 "\n", lvl + 1, psc_misses_per_level[lvl]);
                    double avg_miss_latency = psc_misses_per_level[lvl]
                        ? static_cast<double>(psc_miss_latency_total_cycles[lvl]) / static_cast<double>(psc_misses_per_level[lvl])
                        : 0.0;
                    double miss_share = total_miss_cycles
                        ? static_cast<double>(psc_miss_latency_total_cycles[lvl]) / static_cast<double>(total_miss_cycles) * 100.0
                        : 0.0;
                    fprintf(csv_fp, "proposed_PSC_L%d_avg_miss_latency_cycles,%.2f\n", lvl + 1, avg_miss_latency);
                    fprintf(csv_fp, "proposed_PSC_L%d_miss_latency_share_pct,%.2f\n", lvl + 1, miss_share);
                    String label = String(("proposed_PSC_L" + std::to_string(lvl + 1) + "_miss_latency_cycles").c_str());
                    psc_miss_latency_histograms[lvl].printCsv(csv_fp, label.c_str());
                    std::vector<std::pair<std::string, UInt64>> hitwhere_entries;
                    for (int where = 0; where < HitWhere::NUM_HITWHERES; ++where){
                        UInt64 count = psc_miss_hit_where_counts[lvl][where];
                        if(!count)
                            continue;
                        hitwhere_entries.emplace_back(HitWhereString(static_cast<HitWhere::where_t>(where)), count);
                    }
                    if(!hitwhere_entries.empty()){
                        String hitwhere_label = String(("proposed_PSC_L" + std::to_string(lvl + 1) + "_miss_hitwhere").c_str());
                        printCsvLabeledCounts(csv_fp, hitwhere_label.c_str(), hitwhere_entries);
                    }
                }

            }
            if(!psc_combination_hitwhere_counts.empty()){
                fprintf(csv_fp, "proposed_PSC_combo_hitwhere,combo,None");
                for (int where = 0; where < HitWhere::NUM_HITWHERES; ++where)
                    fprintf(csv_fp, ",%s", HitWhereString(static_cast<HitWhere::where_t>(where)));
                fprintf(csv_fp, "\n");
                for (const auto &entry : psc_combination_hitwhere_counts){
                    fprintf(csv_fp, "proposed_PSC_combo_hitwhere,%s", entry.first.c_str());
                    fprintf(csv_fp, ",%" PRIu64, entry.second[HitWhere::NUM_HITWHERES]);
                    for (int where = 0; where < HitWhere::NUM_HITWHERES; ++where)
                        fprintf(csv_fp, ",%" PRIu64, entry.second[where]);
                    fprintf(csv_fp, "\n");
                }
            }
            if(!psc_miss_hitwhere_pair_counts.empty()){
                std::vector<std::pair<std::string, UInt64>> pair_entries;
                pair_entries.reserve(psc_miss_hitwhere_pair_counts.size());
                for (const auto &entry : psc_miss_hitwhere_pair_counts)
                    pair_entries.emplace_back(entry.first, entry.second);
                printCsvLabeledCounts(csv_fp, "proposed_PSC_miss_hitwhere_pairs", pair_entries);
            }
            UInt64 ptb_pdpt_total = 0;
            for (const auto &row : ptb_pdpt_combo_counts){
                for (UInt64 count : row)
                    ptb_pdpt_total += count;
            }
            if(ptb_pdpt_total > 0){
                std::vector<std::pair<std::string, UInt64>> combo_entries;
                combo_entries.reserve(4);
                combo_entries.emplace_back("PTB-MISS_PDPT-MISS", ptb_pdpt_combo_counts[0][0]);
                combo_entries.emplace_back("PTB-MISS_PDPT-HIT", ptb_pdpt_combo_counts[0][1]);
                combo_entries.emplace_back("PTB-HIT_PDPT-MISS", ptb_pdpt_combo_counts[1][0]);
                combo_entries.emplace_back("PTB-HIT_PDPT-HIT", ptb_pdpt_combo_counts[1][1]);
                printCsvLabeledCounts(csv_fp, "proposed_PTB_PDPT_combo", combo_entries);
            }
            if(!traversal_path_counts.empty()){
                std::vector<std::pair<std::string, UInt64>> path_entries;
                path_entries.reserve(traversal_path_counts.size());
                for(const auto &entry : traversal_path_counts)
                    path_entries.emplace_back(entry.first, entry.second);
                printCsvLabeledCounts(csv_fp, "proposed_PTW_traversal_paths", path_entries);
            }
            stlb_miss_latency_histogram.printCsv(csv_fp, "proposed_TLB_miss_service_latency_cycles");
            double total_ns = static_cast<double>(total_walk_latency.getNS());
            if(total_ns > 0){
                double ptb_share = static_cast<double>(total_ptb_latency.getNS()) / total_ns * 100.0;
                fprintf(csv_fp, "proposed_PTB_latency_share_pct,%.2f\n", ptb_share);
            }
            if(overlap_samples > 0){
                double avg_overlap_ratio = static_cast<double>(overlap_ratio_sum_milli) / static_cast<double>(overlap_samples) / 1000.0;
                double overlap_ready_pct = static_cast<double>(overlap_ready) / static_cast<double>(overlap_samples) * 100.0;
                fprintf(csv_fp, "proposed_PTB_overlap_samples,%" PRIu64 "\n", overlap_samples);
                fprintf(csv_fp, "proposed_PTB_overlap_successes,%" PRIu64 "\n", overlap_ready);
                fprintf(csv_fp, "proposed_PTB_overlap_success_rate_pct,%.2f\n", overlap_ready_pct);
                fprintf(csv_fp, "proposed_PTB_overlap_ratio_avg,%.4f\n", avg_overlap_ratio);
                overlap_ratio_histogram.printCsvCdf(csv_fp, "proposed_PTB_overlap_ratio_milli");
                overlap_tail_latency_histogram.printCsv(csv_fp, "proposed_PTB_overlap_tail_latency_cycles");
            }

            for(int i=0; i< HitWhere::NUM_HITWHERES; i++){
                String label = String(("proposed_PTB_prefetch_latency_" + std::string(HitWhereString(static_cast<HitWhere::where_t>(i)))).c_str());
                prefeth_latency[static_cast<HitWhere::where_t>(i)].printCsv(csv_fp, label.c_str());
            }// 

            fclose(csv_fp);
        }
    }


}
