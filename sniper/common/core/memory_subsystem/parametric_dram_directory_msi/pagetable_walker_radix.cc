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
        if(total == 1){
            min = value;
            max = value;
        } else {
            min = std::min(min, value);
            max = std::max(max, value);
        }
    }

    void ProposedHistogram::print(FILE *fp, const char *label, int width) const{
        if(!fp)
            return;
        UInt64 max_count = 0;
        for (UInt64 count : buckets)
            max_count = std::max(max_count, count);
        fprintf(fp, "%s (total=%" PRIu64 ", min=%" PRIu64 ", max=%" PRIu64 ")\n", label, total, min, max);
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
        psc_miss_hit_where_counts.resize(number_of_levels);
        for (auto &counts : psc_miss_hit_where_counts)
            counts.fill(0);
        rob_stall_psc_level_cycles.resize(number_of_levels, 0);
        psc_accesses = 0;
        psc_misses = 0;
        rob_stall_stlb_miss_cycles = 0;
        traversal_paths_unique_count = 0;
        total_walk_latency = SubsecondTime::Zero();
        total_ptb_latency = SubsecondTime::Zero();
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
            for (int where = 0; where < HitWhere::NUM_HITWHERES; ++where){
                HitWhere::where_t where_type = static_cast<HitWhere::where_t>(where);
                String where_name = String(HitWhereString(where_type));
                String psc_hitwhere_metric = String(("psc_miss_hitwhere_" + std::string(where_name.c_str()) + "_level_" + std::to_string(i + 1) + "_proposed").c_str());
                registerStatsMetric(name, core_id, psc_hitwhere_metric, &psc_miss_hit_where_counts[i][where]);
            }
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

            std::vector<uint64_t> vpn_indices = computeVpnIndices(address);

            SubsecondTime total_latency;
            SubsecondTime t_start;
            SubsecondTime now = getShmemPerfModel()->getElapsedTime(ShmemPerfModel::_USER_THREAD);

            SubsecondTime ptb_latency = SubsecondTime::Zero();
            std::string traversal_path = "DTLB->STLB->PTW";
            auto append_psc_event = [&](int level, const std::string &event) {
                traversal_path += "->PSC-L" + std::to_string(level) + "-" + event;
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
            
            if(ptb){
                PageTableBuffer::LookupResult lookup_result = ptb->lookup(vpn_indices, count);
                ptb_latency = lookup_result.latency;
                if(lookup_result.hit){
                    int start_level = (ptb->getMode() == PageTableBuffer::Mode::LEAF_PT) ? stats_radix.number_of_levels : stats_radix.number_of_levels - 1;
                    ptw_table* start_table = reinterpret_cast<ptw_table*>(lookup_result.base_address);
                    if(count)
                        traversal_path += "->PTB-HIT-L" + std::to_string(start_level);
                    SubsecondTime walk_latency = InitializeWalkRecursive(eip, address, start_level, start_table, lock_signal, data_buf, data_length, modeled, count, traversal_path, true);
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
                        psc_misses++;
                        psc_misses_per_level[level_index]++;
                        psc_miss_latency_histograms[level_index].update(SubsecondTime::divideRounded(total_latency, core->getDvfsDomain()->getPeriod()));
                        psc_miss_hit_where_counts[level_index][hit_where]++;
                        rob_stall_psc_level_cycles[level_index] += SubsecondTime::divideRounded(total_latency, core->getDvfsDomain()->getPeriod());
                    }
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
                return final_latency;
            }


            SubsecondTime final_latency = ptb_latency + total_latency+InitializeWalkRecursive(eip, address,2,starting_table->entries[a1].next_level_table,lock_signal,data_buf,data_length, modeled, count, traversal_path, true);

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


            return final_latency;

    }

    SubsecondTime PageTableWalkerRadix::InitializeWalkRecursive(IntPtr eip, uint64_t address,
        int level,ptw_table* new_table,
        Core::lock_signal_t lock_signal,
        Byte* data_buf, UInt32 data_length,
        bool modeled, bool count, std::string &traversal_path, bool allow_psc_lookup){

            uint64_t a1;
            int shift_bits=0;
            IntPtr pwc_address;
            SubsecondTime t_start;
            SubsecondTime total_latency;
            
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
                    recordLevelStats(level-1, total_latency);
            }
            else{
                    
                    t_start = getShmemPerfModel()->getElapsedTime(ShmemPerfModel::_USER_THREAD);
                    
                    IntPtr cache_address = ((IntPtr)(&new_table->entries[a1])) & (~((64 - 1))); 

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
                    if(page_walk_cache_enabled && count){
                        psc_misses++;
                        psc_misses_per_level[level_index]++;
                        psc_miss_latency_histograms[level_index].update(SubsecondTime::divideRounded(total_latency, core->getDvfsDomain()->getPeriod()));
                        psc_miss_hit_where_counts[level_index][hit_where]++;
                        rob_stall_psc_level_cycles[level_index] += SubsecondTime::divideRounded(total_latency, core->getDvfsDomain()->getPeriod());
                    }
                    if(count){
                        if(page_walk_cache_enabled && allow_psc_lookup)
                            traversal_path += "->PSC-L" + std::to_string(level_index + 1) + "-MISS-" + HitWhereString(hit_where);
                        else
                            traversal_path += "->PSC-L" + std::to_string(level_index + 1) + "-DISABLED";
                    }

            }

            if(new_table->entries[a1].entry_type==ptw_table_entry_type::PTW_NONE){
                new_table->entries[a1]=*CreateNewPtwEntryAtLevel(level,stats_radix.number_of_levels,stats_radix.address_bit_indices,stats_radix.hit_percentages,this, address);
            }
            if(new_table->entries[a1].entry_type==ptw_table_entry_type::PTW_ADDRESS){
                //std::cout<<std::hex<<address<<" - "<<std::hex<<a1<<" - "<<level<<" Address\n";
                return total_latency;
            }
            
            bool ptb_pd_mode = ptb && ptb->getMode() == PageTableBuffer::Mode::PD;
            bool pd_level = ptb_pd_mode && (level_index == stats_radix.number_of_levels - 2);
            bool pd_psc_miss = pd_level && page_walk_cache_enabled && allow_psc_lookup && !pwc_hit;

            // Prefetch the leaf PTE after a PD-level PSC miss (hit or page-fault path).
            if (pd_psc_miss
                && new_table->entries[a1].entry_type == ptw_table_entry_type::PTW_TABLE_POINTER
                && new_table->entries[a1].next_level_table)
            {
                std::vector<uint64_t> vpn_indices = computeVpnIndices(address);
                uint64_t leaf_index = vpn_indices.back();
                ptw_table* leaf_table = new_table->entries[a1].next_level_table;
                IntPtr leaf_address = ((IntPtr)(&leaf_table->entries[leaf_index])) & (~((64 - 1)));
                SubsecondTime prefetch_time = getShmemPerfModel()->getElapsedTime(ShmemPerfModel::_USER_THREAD);
                cache->processMemOpFromCore(
                    eip,
                    lock_signal,
                    Core::mem_op_t::READ,
                    leaf_address, 0,
                    data_buf, data_length,
                    false,
                    false, CacheBlockInfo::block_type_t::PAGE_TABLE, SubsecondTime::Zero());
                pwc->lookup(leaf_address, prefetch_time, true, level + 1, false);
                m_shmem_perf_model->setElapsedTime(ShmemPerfModel::_USER_THREAD, prefetch_time);
            }

            return total_latency+InitializeWalkRecursive(eip,address,level+1,new_table->entries[a1].next_level_table,lock_signal,data_buf,data_length,modeled,count, traversal_path, allow_psc_lookup && !pd_psc_miss);
        
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
        double avg_stall_cycles = walks ? static_cast<double>(SubsecondTime::divideRounded(total_walk_latency, period)) / walks : 0.0;
        double cpi_on_stlb_miss = 1.0 + avg_stall_cycles;

        String output_path = Sim()->getConfig()->formatOutputFileName("proposed.stats");
        FILE *fp = fopen(output_path.c_str(), "a");
        if(fp){
            fprintf(fp, "[Core %d] proposed STLB miss CPI: %.4f (avg stall cycles %.2f over %" PRIu64 " walks)\n",
                    core_id, cpi_on_stlb_miss, avg_stall_cycles, walks);
            if(psc_accesses > 0){
                double psc_miss_rate = (static_cast<double>(psc_misses) / static_cast<double>(psc_accesses)) * 100.0;
                fprintf(fp, "[Core %d] proposed PSC miss rate: %.2f%% (%" PRIu64 "/%" PRIu64 ")\n",
                        core_id, psc_miss_rate, psc_misses, psc_accesses);
                for (int lvl = 0; lvl < stats_radix.number_of_levels; ++lvl){
                    fprintf(fp, "  proposed PSC level %d hits %" PRIu64 ", misses %" PRIu64 "\n",
                            lvl+1, psc_hits_per_level[lvl], psc_misses_per_level[lvl]);
                    String label = String(("  proposed PSC level " + std::to_string(lvl + 1) + " miss latency histogram (cycles)").c_str());
                    psc_miss_latency_histograms[lvl].print(fp, label.c_str());
                    bool printed_hitwhere = false;
                    for (int where = 0; where < HitWhere::NUM_HITWHERES; ++where){
                        UInt64 count = psc_miss_hit_where_counts[lvl][where];
                        if(!count)
                            continue;
                        if(!printed_hitwhere){
                            fprintf(fp, "    proposed PSC level %d miss HitWhere histogram:\n", lvl+1);
                            printed_hitwhere = true;
                        }
                        fprintf(fp, "      %s: %" PRIu64 "\n", HitWhereString(static_cast<HitWhere::where_t>(where)), count);
                    }
                }
            }
            if(!traversal_path_counts.empty()){
                fprintf(fp, "[Core %d] proposed PTW traversal paths (%" PRIu64 "):\n", core_id, traversal_paths_unique_count);
                for(const auto &entry : traversal_path_counts){
                    fprintf(fp, "  %s: %" PRIu64 "\n", entry.first.c_str(), entry.second);
                }
            }
            String tlb_label(("[Core " + std::to_string(core_id) + "] proposed TLB miss service latency histogram (cycles)").c_str());
            stlb_miss_latency_histogram.print(fp, tlb_label.c_str());
            double total_ns = static_cast<double>(total_walk_latency.getNS());
            if(total_ns > 0){
                double ptb_share = static_cast<double>(total_ptb_latency.getNS()) / total_ns * 100.0;
                fprintf(fp, "[Core %d] proposed PTB latency share: %.2f%%\n", core_id, ptb_share);
            }
            fclose(fp);
        }
    }


}