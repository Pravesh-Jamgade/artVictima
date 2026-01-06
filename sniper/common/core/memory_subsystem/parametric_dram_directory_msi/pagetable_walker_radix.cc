#include "pagetable_walker_radix.h"
#include "cache_cntlr.h"
#include "pwc.h"
#include "subsecond_time.h"
#include <math.h> 
#include <fstream>
#include <inttypes.h>
#include <stdlib.h>
#include <time.h>


namespace ParametricDramDirectoryMSI{

    int PageTableWalkerRadix::counter = 0;

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
        total_walk_latency = SubsecondTime::Zero();
        total_ptb_latency = SubsecondTime::Zero();
        String name = "ptw_radix_";
        name = name+std::to_string(counter).c_str();
        for (int i = 0; i < number_of_levels; i++){
            String metric_name = "page_level_latency_";
            String metric = metric_name+std::to_string(i).c_str();
            registerStatsMetric(name, core_id, metric, &latency_per_level[i]);
        }
        
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
            if(ptb){
                PageTableBuffer::LookupResult lookup_result = ptb->lookup(vpn_indices, count);
                ptb_latency = lookup_result.latency;
                if(lookup_result.hit){
                    int start_level = (ptb->getMode() == PageTableBuffer::Mode::LEAF_PT) ? stats_radix.number_of_levels : stats_radix.number_of_levels - 1;
                    ptw_table* start_table = reinterpret_cast<ptw_table*>(lookup_result.base_address);
                    SubsecondTime walk_latency = InitializeWalkRecursive(eip, address, start_level, start_table, lock_signal, data_buf, data_length, modeled, count);
                    SubsecondTime final_latency = ptb_latency + walk_latency;
                    total_ptb_latency += ptb_latency;
                    total_walk_latency += final_latency;
                    m_shmem_perf_model->setElapsedTime(ShmemPerfModel::_USER_THREAD,now);
                    UInt64 vpn = address >> init_walk_functional(address);
                    track_per_page_ptw_latency(vpn,final_latency);
                    return final_latency;
                }
                total_ptb_latency += ptb_latency;
            }

            uint64_t a1 = vpn_indices[0];
            bool pwc_hit = false;

            if(page_walk_cache_enabled){ //@kanellok access page walk caches

                            PWC::where_t pwc_where;

                            if(page_walk_cache_enabled)
                {
                    IntPtr pwc_address = (IntPtr)(&starting_table->entries[a1]);
                    pwc_where = pwc->lookup(pwc_address, t_start ,true, 1, count);
                    if( pwc_where == PWC::HIT ) pwc_hit = true;

                }

            }

            bool level0_recorded = false;
            bool level_recorded = false;
            if(pwc_hit == true){

                    total_latency = pwc->access_latency.getLatency();

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
                    level0_recorded = true;

            }

            if(!level0_recorded)
                recordLevelStats(0, total_latency);


            if(starting_table->entries[a1].entry_type==ptw_table_entry_type::PTW_NONE){
                starting_table->entries[a1]=*CreateNewPtwEntryAtLevel(1,stats_radix.number_of_levels,stats_radix.address_bit_indices,stats_radix.hit_percentages,this,address);
            }
            if(starting_table->entries[a1].entry_type==ptw_table_entry_type::PTW_ADDRESS){
                //std::cout<<std::hex<<address<<" - "<<std::hex<<a1<<" - "<<level<<" Address\n";
                return total_latency + ptb_latency;
            }


            SubsecondTime final_latency = ptb_latency + total_latency+InitializeWalkRecursive(eip, address,2,starting_table->entries[a1].next_level_table,lock_signal,data_buf,data_length, modeled, count);

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


            return final_latency;

    }

    SubsecondTime PageTableWalkerRadix::InitializeWalkRecursive(IntPtr eip, uint64_t address,
        int level,ptw_table* new_table,
        Core::lock_signal_t lock_signal,
        Byte* data_buf, UInt32 data_length,
        bool modeled, bool count){

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

            if(page_walk_cache_enabled){ //@kanellok access page walk caches 

			    PWC::where_t pwc_where;

			    if(page_walk_cache_enabled && level != (stats_radix.number_of_levels) )
                {
                    pwc_address = (IntPtr)(&new_table->entries[a1]);
                    pwc_where = pwc->lookup(pwc_address, t_start ,true, level, count);
                    if( pwc_where == PWC::HIT ) pwc_hit = true; 

                }
            }
		
            if(pwc_hit == true){

                    total_latency = pwc->access_latency.getLatency(); 

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
                    
                    if(page_walk_cache_enabled)
                        total_latency = t_end - t_start + pwc->miss_latency.getLatency();
                    else
                        total_latency = t_end - t_start;
                    
                    addresses.push_back((IntPtr)(&new_table->entries[a1]));

                    mem_manager->tagCachesBlockType(cache_address,CacheBlockInfo::block_type_t::PAGE_TABLE);
                    recordLevelStats(level-1, total_latency, &hit_where);
                    level_recorded = true;

             }

            if(!level_recorded)
                recordLevelStats(level-1, total_latency);
		    


            if(new_table->entries[a1].entry_type==ptw_table_entry_type::PTW_NONE){
                new_table->entries[a1]=*CreateNewPtwEntryAtLevel(level,stats_radix.number_of_levels,stats_radix.address_bit_indices,stats_radix.hit_percentages,this, address);
            }
            if(new_table->entries[a1].entry_type==ptw_table_entry_type::PTW_ADDRESS){
                //std::cout<<std::hex<<address<<" - "<<std::hex<<a1<<" - "<<level<<" Address\n";
                return total_latency;
            }
            
            
            
            return total_latency+InitializeWalkRecursive(eip,address,level+1,new_table->entries[a1].next_level_table,lock_signal,data_buf,data_length,modeled,count);
        
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

        printf("[Core %d] STLB miss CPI: %.4f (avg stall cycles %.2f over %" PRIu64 " walks)\n", core_id, cpi_on_stlb_miss, avg_stall_cycles, walks);

        double total_ns = static_cast<double>(total_walk_latency.getNS());
        if(total_ns > 0){
            double ptb_share = static_cast<double>(total_ptb_latency.getNS()) / total_ns * 100.0;
            printf("  PTB latency share: %.2f%%\n", ptb_share);
            for (int lvl = 0; lvl < stats_radix.number_of_levels; ++lvl){
                double level_ns = static_cast<double>(latency_per_level[lvl].getNS());
                double level_pct = level_ns / total_ns * 100.0;
                double avg_ns = level_accesses[lvl] ? level_ns / level_accesses[lvl] : 0.0;
                printf("  Level %d latency: avg %.2f ns, share %.2f%%, accesses %" PRIu64 "\n", lvl+1, avg_ns, level_pct, level_accesses[lvl]);
                printf("    Latency histogram: ");
                latency_histograms[lvl].print();
                if(!hit_where_histograms[lvl].empty()){
                    printf("    HitWhere histogram:\n");
                    for(const auto &entry : hit_where_histograms[lvl]){
                        UInt64 count = entry.second;
                        SubsecondTime lat_sum = hit_where_latency[lvl].at(entry.first);
                        double avg_hw_ns = count ? static_cast<double>(lat_sum.getNS()) / count : 0.0;
                        printf("      %s: %" PRIu64 " (avg %.2f ns)\n", HitWhereString(entry.first), count, avg_hw_ns);
                    }
                }
            }
        }
    }


}